from datetime import datetime

from pydantic import BaseModel


class TaskData(BaseModel):
    task_id: int
    user_id: int
    title: str
    body: str = ""
    completed: bool = False
    deadline: datetime
    priority: int = 2
    category: str = ""

    @classmethod
    def from_bytes(cls, body: bytes):
        return cls.model_validate_json(body)

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
