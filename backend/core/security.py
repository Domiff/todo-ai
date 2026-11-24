from datetime import timedelta

import jwt
from authx import AuthX, AuthXConfig

from backend.core.settings import settings

config = AuthXConfig(
    JWT_ALGORITHM=settings.auth.JWT_ALGORITHM,
    JWT_TOKEN_LOCATION=["headers"],
    JWT_PUBLIC_KEY=settings.auth.JWT_PUBLIC_KEY.read_text(),
)
auth = AuthX(config=config)
