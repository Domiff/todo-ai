from fastapi import APIRouter

from backend.assistant.schemas import QuestionSchema
from backend.core.http import http_client_manager
from backend.core.settings import settings

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/ask")
async def ask(question: QuestionSchema):
    client = http_client_manager.get_client()
    response = await client.post(
        f"{settings.ai.AI_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.ai.API_KEY}"},
        json={
            "model": settings.ai.MODEL,
            "messages": [{"role": "user", "content": question.text}],
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
