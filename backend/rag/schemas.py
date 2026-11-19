from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class TaskEventTypes(StrEnum):
    CREATED_EVENT = "todo.task.created.v1"
    UPDATED_EVENT = "todo.task.updated.v1"
    DELETED_EVENT = "todo.task.deleted.v1"


class TaskData(BaseModel):
    task_id: int
    user_id: int
    title: str
    body: str = ""
    completed: bool = False
    deadline: datetime
    priority: int = 2
    category: str = ""

    def to_text(self) -> str:
        parts = [self.title]
        if self.body:
            parts.append(self.body)
        if self.category:
            parts.append(f"Категория: {self.category}")
        return "\n".join(parts)


class SearchResult(BaseModel):
    task_id: int
    score: float
    text: str
