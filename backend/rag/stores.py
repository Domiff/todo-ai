from qdrant_client import AsyncQdrantClient, models

from backend.core.settings import settings
from backend.infrastructures.qdrant import get_client
from backend.rag.schemas import SearchResult, TaskData


class QdrantStore:
    def __init__(
        self,
        collection: str,
        model: str,
        models_dir: str,
        top_k: int,
        score_threshold: float | None,
    ) -> None:
        self.collection = collection
        self.model = model
        self.options = {"cache_dir": models_dir}
        self.top_k = top_k
        self.score_threshold = score_threshold

    @property
    def client(self) -> AsyncQdrantClient:
        return get_client()

    def _document(self, text: str) -> models.Document:
        return models.Document(text=text, model=self.model, options=self.options)

    @staticmethod
    def _payload(task: TaskData) -> dict:
        return {
            "user_id": task.user_id,
            "title": task.title,
            "completed": task.completed,
            "priority": task.priority,
            "deadline": task.deadline.isoformat(),
            "category": task.category,
            "text": task.to_text(),
        }

    async def ensure_collection(self) -> None:
        if await self.client.collection_exists(self.collection):
            return

        await self.client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=self.client.get_embedding_size(self.model),
                distance=models.Distance.COSINE,
            ),
        )

        await self.client.create_payload_index(
            collection_name=self.collection,
            field_name="user_id",
            field_schema=models.PayloadSchemaType.INTEGER,
        )

        await self.client.create_payload_index(
            collection_name=self.collection,
            field_name="completed",
            field_schema=models.PayloadSchemaType.BOOL,
        )

    async def upsert(self, task: TaskData) -> None:
        await self.client.upsert(
            collection_name=self.collection,
            points=[
                models.PointStruct(
                    id=task.task_id,
                    vector=self._document(task.to_text()),
                    payload=self._payload(task),
                )
            ],
        )

    async def update_payload(self, task: TaskData) -> None:
        exists = await self.client.retrieve(
            collection_name=self.collection,
            ids=[task.task_id],
            with_payload=False,
        )
        if not exists:
            await self.upsert(task)
            return

        await self.client.set_payload(
            collection_name=self.collection,
            payload=self._payload(task),
            points=[task.task_id],
        )

    async def get_text(self, task_id: int) -> str | None:
        points = await self.client.retrieve(
            collection_name=self.collection,
            ids=[task_id],
            with_payload=["text"],
        )
        if not points:
            return None
        return points[0].payload["text"]

    async def delete(self, task_id: int) -> None:
        await self.client.delete(
            collection_name=self.collection,
            points_selector=[task_id],
        )

    async def search(
        self,
        query: str,
        user_id: int,
        limit: int | None = None,
    ) -> list[SearchResult]:
        result = await self.client.query_points(
            collection_name=self.collection,
            query=self._document(query),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="user_id", match=models.MatchValue(value=user_id)
                    )
                ]
            ),
            limit=limit or self.top_k,
            score_threshold=self.score_threshold,
            with_payload=True,
        )
        return [
            SearchResult(
                task_id=point.id, score=point.score, text=point.payload["text"]
            )
            for point in result.points
        ]


qdrant_store = QdrantStore(
    collection=settings.rag.RAG_COLLECTION,
    model=settings.rag.RAG_EMBEDDING_MODEL,
    models_dir=settings.rag.RAG_MODELS_DIR,
    top_k=settings.rag.RAG_TOP_K,
    score_threshold=settings.rag.RAG_SCORE_THRESHOLD,
)
