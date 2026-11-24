from fastapi import APIRouter

from backend.assistant.schemas import QuestionSchema, AnswerSchema
from backend.assistant.services import get_answer
from backend.core.depends import CurrentUserIdDep

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/ask")
async def ask(question: QuestionSchema, current_user_id: CurrentUserIdDep) -> AnswerSchema:
    return AnswerSchema(text=await get_answer(question, current_user_id))
