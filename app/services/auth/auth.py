from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import UnauthorizedException
from app.core.security.password import verify_password
from app.core.security.tokens import create_access_token
from app.database.postgres import get_session
from app.repositories.user import UserRepository
from app.schemas.user import LoginRequest, TokenOut


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def login(self, data: LoginRequest) -> TokenOut:
        user = await self.users.get_by_email(data.email)
        # Same message for unknown email and wrong password, so emails can't be probed.
        if not user or not verify_password(data.password, user.password_hash) or not user.is_active:
            raise UnauthorizedException("Invalid email or password")
        return TokenOut(access_token=create_access_token(user.id))


def get_auth_service(session: AsyncSession = Depends(get_session)) -> AuthService:
    return AuthService(session)
