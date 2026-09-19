import secrets

from fastapi import Depends, Security
from fastapi.security import APIKeyHeader, HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import settings
from app.core.exc import UnauthorizedException
from app.database.postgres import get_session
from app.services.auth.dependencies import get_current_user

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
_bearer = HTTPBearer(auto_error=False)


async def require_integration_access(
    api_key: str | None = Security(_api_key_header),
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> None:
    """Either the shared API key (unattended automations) or a logged-in user's token (a person pressing a button)."""
    if api_key is not None:
        expected = settings.integration.API_KEY
        # Constant-time comparison, so the key can't be guessed from response timing.
        if not expected or not secrets.compare_digest(api_key.encode(), expected.encode()):
            raise UnauthorizedException("Invalid API key")
        return
    if credentials is None:
        raise UnauthorizedException("Log in or send the X-API-Key header")
    await get_current_user(credentials=credentials, session=session)
