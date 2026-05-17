from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings

_bearer = HTTPBearer(auto_error=False)


async def require_owner(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
) -> None:
    settings = get_settings()
    if not credentials or credentials.credentials != settings.muai_api_secret:
        raise HTTPException(status_code=401, detail="Unauthorized")
