from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, User)

    async def get_by_login(self, wms_login: str) -> User | None:
        # Case-insensitive: "JKOWALSKI" and "jkowalski" are the same operator.
        query = select(User).where(func.lower(User.wms_login) == wms_login.strip().lower())
        return (await self.session.execute(query)).scalar_one_or_none()
