import asyncio
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager
from datetime import datetime
from uuid import UUID

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection
from pydantic import BaseModel, ConfigDict

from backend.core.logging import get_logger
from backend.core.settings import settings

TASK_QUEUE = "todo-ai.tasks"
Handler = Callable[[bytes], Awaitable[None]]
logger = get_logger(name=__name__)

connection: AbstractRobustConnection | None = None
channel: AbstractChannel | None = None
lock = asyncio.Lock()


class Event[DataT: BaseModel](BaseModel):
    model_config = ConfigDict(frozen=True)

    specversion: str
    id: UUID
    source: str
    type: str
    time: datetime
    subject: str | None = None
    datacontenttype: str
    data: DataT

    @classmethod
    def from_bytes(cls, body: bytes) -> Event[DataT]:
        return cls.model_validate_json(body)


class _EventType(BaseModel):
    type: str


def get_event_type(body: bytes) -> str:
    return _EventType.model_validate_json(body).type


async def consume(handler: Handler, queue_name: str) -> None:
    try:
        channel = get_channel()
        queue = await channel.get_queue(name=queue_name, ensure=False)
        await channel.set_qos(prefetch_count=10)

        async with queue.iterator() as iterator:
            async for message in iterator:
                try:
                    async with message.process():
                        await handler(message.body)
                except Exception:
                    logger.exception(
                        "Failed to handle message",
                        extra={
                            "message_id": message.message_id,
                            "routing_key": message.routing_key,
                        },
                    )
    except Exception:
        logger.exception("Consumer stopped", extra={"queue": queue_name})
        raise


@asynccontextmanager
async def consumer(handler: Handler, queue_name: str):
    task = asyncio.create_task(consume(handler, queue_name))
    try:
        yield
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)


async def connect() -> None:
    global connection, channel

    async with lock:
        if connection is None or connection.is_closed:
            connection = await connect_robust(url=settings.rabbitmq.url)
        if channel is None or channel.is_closed:
            channel = await connection.channel()

    logger.info("Connected to RabbitMQ")


async def disconnect() -> None:
    global connection, channel

    if connection is not None and not connection.is_closed:
        await connection.close()
    connection = channel = None

    logger.info("Disconnected from RabbitMQ")


def get_channel() -> AbstractChannel:
    if channel is None or channel.is_closed:
        raise RuntimeError("RabbitMQ is not connected")
    return channel
