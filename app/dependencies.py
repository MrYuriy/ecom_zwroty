from typing import Annotated

from fastapi import Depends

from app.core.security.rbac import require_roles
from app.enums.user import RoleEnum
from app.schemas.user import UserOut
from app.services.auth.auth import AuthService, get_auth_service
from app.services.auth.dependencies import get_current_user
from app.services.user import UserService, get_user_service

AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
UserServiceDep = Annotated[UserService, Depends(get_user_service)]

CurrentUserDep = Annotated[UserOut, Depends(get_current_user)]
AdminUserDep = Annotated[UserOut, Depends(require_roles(RoleEnum.ADMIN))]
