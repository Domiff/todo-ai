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


class Settings(AppSettings):
    app: AppSettings = AppSettings()
    rabbit: RabbitMQSettings = RabbitMQSettings()
    http: HTTPSettings = HTTPSettings()
    ai: AISettings = AISettings()


settings = Settings()
