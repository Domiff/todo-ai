from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR: Path = Path(__file__).parent.parent.parent


class AppSettings(BaseSettings):
    APP_TITLE: str = "Todo AI"
    APP_VERSION: str = "1"

    IS_DEBUG: bool = Field(default=True)

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env", env_file_encoding="utf-8", extra="ignore"
    )


class RabbitMQSettings(AppSettings):
    RABBITMQ_USER: str
    RABBITMQ_PASSWORD: str
    RABBITMQ_HOST: str = "localhost"
    RABBITMQ_PORT: int = 5672

    @property
    def url(self) -> str:
        return (
            f"amqp://{self.RABBITMQ_USER}:{self.RABBITMQ_PASSWORD}"
            f"@{self.RABBITMQ_HOST}:{self.RABBITMQ_PORT}//"
        )


class HTTPSettings(AppSettings):
    TIMEOUT: float = 30.0
    CONNECT: float = 5.0
    MAX_CONNECTIONS: int = 100
    MAX_KEEPALIVE_CONNECTIONS: int = 20
    KEEPALIVE_EXPIRY: float = 30.0
    VERIFY_SSL: bool = True
    PROXY: str | None = None
    PROXY_HOSTS: list[str]


class AISettings(AppSettings):
    API_KEY: str
    MODEL: str
    AI_URL: str


class QdrantSettings(AppSettings):
    QDRANT_HOST: str
    QDRANT_PORT: int

    @property
    def url(self) -> str:
        return f"http://{self.QDRANT_HOST}:{self.QDRANT_PORT}"


class RagSettings(AppSettings):
    RAG_COLLECTION: str = "tasks"
    RAG_EMBEDDING_MODEL: str = "Qwen/Qwen3-Embedding-0.6B-Q"
    RAG_MODELS_DIR: str = str(BASE_DIR / "models")
    RAG_TOP_K: int = 5
    RAG_SCORE_THRESHOLD: float | None = None


class UvicornSettings(AppSettings):
    UVICORN_HOST: str = "0.0.0.0"
    UVICORN_PORT: int = 8020
    UVICORN_PROXY_HEADERS: bool = True
    UVICORN_FORWARDED_ALLOW_IPS: str = "*"
    UVICORN_ROOT_PATH: str = ""


class Settings(AppSettings):
    app: AppSettings = AppSettings()
    rabbitmq: RabbitMQSettings = RabbitMQSettings()
    http: HTTPSettings = HTTPSettings()
    ai: AISettings = AISettings()
    qdrant: QdrantSettings = QdrantSettings()
    rag: RagSettings = RagSettings()
    uvicorn: UvicornSettings = UvicornSettings()


settings = Settings()
