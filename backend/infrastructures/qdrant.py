from qdrant_client import AsyncQdrantClient

from backend.core.logging import get_logger
from backend.core.settings import settings

client: AsyncQdrantClient | None = None
logger = get_logger(name=__name__)


async def connect() -> None:
    global client

    if client is None:
        client = AsyncQdrantClient(url=settings.qdrant.url)
    await client.info()

    logger.info("Connected to Qdrant server")


async def disconnect() -> None:
    global client

    if client is not None:
        await client.close()
    client = None

    logger.info("Disconnected from Qdrant server")


def get_client() -> AsyncQdrantClient:
    if client is None:
        raise RuntimeError("Qdrant is not connected")
    return client
