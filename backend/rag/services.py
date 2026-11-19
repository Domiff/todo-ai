from backend.core.logging import get_logger
from backend.rag.schemas import SearchResult, TaskData
from backend.rag.stores import QdrantStore, qdrant_store

logger = get_logger(__name__)


class QdrantService:
    def __init__(self, store: QdrantStore) -> None:
        self.store = store

    async def index_task(self, task: TaskData) -> None:
        stored_text = await self.store.get_text(task.task_id)
        if stored_text == task.to_text():
            await self.store.update_payload(task)
            action = "update_payload"
        else:
            await self.store.upsert(task)
            action = "upsert"
        logger.info(
            "rag index",
            extra={"task_id": task.task_id, "user_id": task.user_id, "action": action},
        )

    async def delete_task(self, task_id: int) -> None:
        await self.store.delete(task_id)
        logger.info("rag delete", extra={"task_id": task_id})

    async def search_tasks(
        self, question: str, user_id: int, limit: int | None = None
    ) -> list[SearchResult]:
        results = await self.store.search(query=question, user_id=user_id, limit=limit)
        logger.info(
            "rag search",
            extra={
                "user_id": user_id,
                "found": len(results),
                "scores": [round(result.score, 3) for result in results],
            },
        )
        return results


qdrant_service = QdrantService(store=qdrant_store)
