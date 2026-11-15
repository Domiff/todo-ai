from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.assistant.router import router as assistant_router
from backend.core.http import http_client_manager
from backend.core.settings import settings
from backend.core.logging import get_logger, setup_logging
from backend.infrastructures import rabbitmq

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await http_client_manager.startup()
    await rabbitmq.connect()

    try:
        yield
    finally:
        await http_client_manager.shutdown()
        await rabbitmq.disconnect()


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title=settings.app.APP_TITLE,
        version=settings.app.APP_VERSION,
        lifespan=lifespan,
        openapi_url="/openapi.json" if settings.app.IS_DEBUG else None,
    )
    app.include_router(assistant_router)

    return app
