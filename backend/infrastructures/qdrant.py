from qdrant_client import AsyncQdrantClient

from backend.core.settings import settings

client: AsyncQdrantClient | None = None


async def connect() -> None:
    global client

    if client is None:
        client = AsyncQdrantClient(url=settings.qdrant.url)
    await client.info()


async def disconnect() -> None:
    global client

    if client is not None:
        await client.close()
    client = None


def get_client() -> AsyncQdrantClient:
    if client is None:
        raise RuntimeError("Qdrant is not connected")
    return client
