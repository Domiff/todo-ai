from pydantic import BaseModel


class QuestionSchema(BaseModel):
    text: str


class AnswerSchema(BaseModel):
    text: str
