from pydantic import BaseModel


class QuestionSchema(BaseModel):
    user_id: int
    text: str


class AnswerSchema(BaseModel):
    text: str
