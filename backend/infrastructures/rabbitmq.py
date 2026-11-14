import asyncio
import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from aio_pika import connect_robust
from aio_pika.abc import AbstractChannel, AbstractRobustConnection

from backend.core.settings import settings

TASKS_EXCHANGE = "todo.ai"

connection: AbstractRobustConnection | None = None
channel: AbstractChannel | None = None
lock = asyncio.Lock()


@dataclass(frozen=True, kw_only=True)
class Event:
    specversion: str = "1.0"
    id: UUID = field(default_factory=uuid4)
    source: str = "todo-api"
    type: str
    time: datetime = field(default_factory=lambda: datetime.now(UTC))
    subject: str
    datacontenttype: str = "application/json"
    data: Any

    @staticmethod
    def _to_json_value(value: object):
        if isinstance(value, UUID):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        raise TypeError(f"{type(value).__name__} is not JSON serializable")

    def to_bytes(self) -> bytes:
        return json.dumps(asdict(self), default=self._to_json_value).encode()


async def connect() -> None:
    global connection, channel

    async with lock:
        if connection is None or connection.is_closed:
            connection = await connect_robust(url=settings.rabbit.url)
        if channel is None or channel.is_closed:
            channel = await connection.channel()


async def close() -> None:
    global connection, channel

    if connection is not None and not connection.is_closed:
        await connection.close()
    connection = channel = None


def get_channel() -> AbstractChannel:
    if channel is None or channel.is_closed:
        raise RuntimeError("RabbitMQ is not connected")
    return channel
