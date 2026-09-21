from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exc.base import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    ObjectAlreadyExistsException,
    ObjectNotFoundException,
    UnauthorizedException,
)

_STATUS_BY_EXCEPTION: dict[type[Exception], int] = {
    ObjectNotFoundException: 404,
    ObjectAlreadyExistsException: 409,
    ConflictException: 409,
    BadRequestException: 400,
    UnauthorizedException: 401,
    ForbiddenException: 403,
}


def register_exception_handlers(app: FastAPI) -> None:
    for exc_type, status_code in _STATUS_BY_EXCEPTION.items():

        async def _handler(_: Request, exc: Exception, status_code: int = status_code) -> JSONResponse:
            return JSONResponse(status_code=status_code, content={"detail": exc.message})

        app.add_exception_handler(exc_type, _handler)
