from backend.infrastructures.rabbitmq import Event, get_event_type
from backend.rag.schemas import TaskData, TaskEventTypes
from backend.rag.services import qdrant_service


async def handle_task_event(body: bytes) -> None:
    event_type = get_event_type(body)
    if event_type not in TaskEventTypes:
        raise ValueError(f"Unexpected event type: {event_type}")

    task = Event[TaskData].from_bytes(body).data
    if event_type == TaskEventTypes.DELETED_EVENT:
        await qdrant_service.delete_task(task.task_id)
    else:
        await qdrant_service.index_task(task)
