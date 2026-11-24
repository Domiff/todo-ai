from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from backend.core.http import http_client_manager
from backend.core.security import auth
from backend.core.settings import settings


async def get_current_user_id(request: Request) -> int:
    token = await auth.get_access_token_from_request(
        request=request, locations=["headers"]
    )

    response = await http_client_manager.get_client().post(
        f"{settings.auth.AUTH_URL}/auth/verify",
        headers={"Authorization": f"Bearer {token.token}"},
    )
    if response.status_code != status.HTTP_200_OK:
        
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    return int(response.json()["id"])


CurrentUserIdDep = Annotated[int, Depends(get_current_user_id)]
