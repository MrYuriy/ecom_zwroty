from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import UnauthorizedException
from app.core.security.tokens import decode_access_token
from app.database.postgres import get_session
from app.repositories.user import UserRepository
from app.schemas.user import UserOut

_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    session: AsyncSession = Depends(get_session),
) -> UserOut:
    if credentials is None:
        raise UnauthorizedException("Missing bearer token")
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError):
        raise UnauthorizedException("Invalid token") from None
    user = await UserRepository(session).get_one(id=user_id)
    # A deactivated operator loses access immediately, not when the token expires.
    if not user or not user.is_active:
        raise UnauthorizedException("User not found or inactive")
    return UserOut.model_validate(user)
