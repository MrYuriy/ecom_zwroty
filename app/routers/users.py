from fastapi import APIRouter, Query

from app.dependencies import AdminUserDep, UserServiceDep
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserOut, UserUpdate

router = APIRouter(prefix="/users", tags=["Users"])


@router.post("", response_model=UserOut, status_code=201)
async def create_user(data: UserCreate, service: UserServiceDep, _: AdminUserDep) -> UserOut:
    return await service.create_user(data)


@router.get("", response_model=Page[UserOut])
async def list_users(
    service: UserServiceDep,
    _: AdminUserDep,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
) -> Page[UserOut]:
    return await service.list_users(page, limit)


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(user_id: int, data: UserUpdate, service: UserServiceDep, admin: AdminUserDep) -> UserOut:
    return await service.update_user(user_id, data, acting_user_id=admin.id)
