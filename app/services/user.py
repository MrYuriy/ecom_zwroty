from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exc import BadRequestException, ObjectAlreadyExistsException, ObjectNotFoundException
from app.core.security.password import hash_password
from app.database.postgres import get_session
from app.repositories.user import UserRepository
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut, UserUpdate


class UserService:
    def __init__(self, session: AsyncSession) -> None:
        self.users = UserRepository(session)

    async def create_user(self, data: UserCreate) -> UserOut:
        if await self.users.get_by_email(data.email):
            raise ObjectAlreadyExistsException(data.email, "User")
        user = await self.users.create_one(
            {
                "email": data.email,
                "password_hash": hash_password(data.password),
                "full_name": data.full_name,
                "role": data.role,
            }
        )
        return UserOut.model_validate(user)

    async def list_users(self, page: int, limit: int) -> Page[UserOut]:
        users, total = await self.users.get_many(page=page, limit=limit, order_by=[self.users.model.full_name])
        return Page(items=[UserOut.model_validate(u) for u in users], total=total, page=page, limit=limit)

    async def get_user(self, user_id: int) -> UserOut:
        user = await self.users.get_one(id=user_id)
        if not user:
            raise ObjectNotFoundException(user_id, "User")
        return UserOut.model_validate(user)

    async def update_user(self, user_id: int, data: UserUpdate, acting_user_id: int) -> UserOut:
        user = await self.users.get_one(id=user_id)
        if not user:
            raise ObjectNotFoundException(user_id, "User")
        changes = {k: v for k, v in data.model_dump(exclude_unset=True, exclude={"password"}).items() if v is not None}
        # An admin locking themselves out would leave nobody able to manage users.
        if user_id == acting_user_id and (changes.get("is_active") is False or "role" in changes):
            raise BadRequestException("You cannot deactivate yourself or change your own role")
        if data.password:
            changes["password_hash"] = hash_password(data.password)
        user = await self.users.update_one(user, changes)
        return UserOut.model_validate(user)


def get_user_service(session: AsyncSession = Depends(get_session)) -> UserService:
    return UserService(session)
