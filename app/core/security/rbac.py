from fastapi import Depends

from app.core.exc import ForbiddenException
from app.enums.user import RoleEnum
from app.schemas.user import UserOut
from app.services.auth.dependencies import get_current_user


def require_roles(*roles: RoleEnum):
    async def _check(current_user: UserOut = Depends(get_current_user)) -> UserOut:
        if current_user.role not in roles:
            raise ForbiddenException("Insufficient role")
        return current_user

    return _check
