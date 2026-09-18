from fastapi import APIRouter

from app.dependencies import AuthServiceDep, CurrentUserDep
from app.schemas.user import LoginRequest, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/login", response_model=TokenOut)
async def login(data: LoginRequest, service: AuthServiceDep) -> TokenOut:
    return await service.login(data)


@router.get("/me", response_model=UserOut)
async def me(current_user: CurrentUserDep) -> UserOut:
    return current_user
