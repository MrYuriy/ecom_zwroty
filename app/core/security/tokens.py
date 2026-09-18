from datetime import UTC, datetime, timedelta
from uuid import uuid4

from jose import JWTError, jwt

from app.core import settings
from app.core.exc import UnauthorizedException


def create_access_token(subject: str | int) -> str:
    now = datetime.now(UTC)
    payload = {
        "sub": str(subject),
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt.EXPIRE_MINUTES),
        "jti": str(uuid4()),
    }
    return jwt.encode(payload, settings.jwt.SECRET_KEY, algorithm=settings.jwt.ALGORITHM)


def decode_access_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.jwt.SECRET_KEY, algorithms=[settings.jwt.ALGORITHM])
    except JWTError:
        raise UnauthorizedException("Invalid or expired token")
