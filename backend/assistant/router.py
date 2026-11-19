from fastapi import APIRouter

from backend.assistant.schemas import QuestionSchema, AnswerSchema
from backend.assistant.services import get_answer

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/ask")
async def ask(question: QuestionSchema) -> AnswerSchema:
    return AnswerSchema(text=await get_answer(question))
