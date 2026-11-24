from string import Template

from backend.core.http import http_client_manager
from backend.core.settings import settings
from backend.rag.schemas import SearchResult
from backend.rag.services import qdrant_service
from backend.assistant.schemas import QuestionSchema

SYSTEM_PROMPT = Template(
    """
    Ты — помощник в приложении задач. Отвечай кратко, по-русски.
    Отвечай только по задачам пользователя из списка ниже.
    Если в списке нет ответа — так и скажи, ничего не выдумывай.
    
    Задачи пользователя:
    $context
    """
)


async def ask(messages: list[dict]) -> str:
    client = http_client_manager.get_client()
    response = await client.post(
        f"{settings.ai.AI_URL}/chat/completions",
        headers={"Authorization": f"Bearer {settings.ai.API_KEY}"},
        json={
            "model": settings.ai.MODEL,
            "messages": messages,
        },
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def build_context(results: list[SearchResult]) -> str:
    if not results:
        return "Подходящих задач не найдено."
    return "\n\n".join(f"Задача {r.task_id}:\n{r.text}" for r in results)


async def get_answer(question: QuestionSchema, user_id: int) -> str:
    results = await qdrant_service.search_tasks(
        question=question.text, user_id=user_id
    )
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT.substitute(context=build_context(results)),
        },
        {"role": "user", "content": question.text},
    ]
    return await ask(messages)
