import os

# Settings require DATABASE_URL at import; tests never touch a real database.
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core import settings  # noqa: E402
from app.core.security.password import hash_password  # noqa: E402
from app.database.postgres import get_session  # noqa: E402
from app.enums.user import RoleEnum  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base, LineImage, OrderLine, ReturnOrder, Sku, User, WmsOrder  # noqa: E402

# Order matters for FKs.
TEST_TABLES = [
    User.__table__,
    Sku.__table__,
    ReturnOrder.__table__,
    OrderLine.__table__,
    LineImage.__table__,
    WmsOrder.__table__,
]

PASSWORD = "Str0ng-pass"


@pytest.fixture(autouse=True)
def uploads_dir(tmp_path, monkeypatch):
    # Uploaded images land in a per-test temp dir, never in the real uploads folder.
    path = tmp_path / "uploads"
    monkeypatch.setattr(settings.storage, "UPLOADS_DIR", str(path))
    return path


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine("sqlite+aiosqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    async with eng.begin() as conn:
        await conn.run_sync(lambda sync_conn: Base.metadata.create_all(sync_conn, tables=TEST_TABLES))
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def app(session_factory):
    application = create_app()

    async def _override_get_session():
        async with session_factory() as session:
            yield session

    application.dependency_overrides[get_session] = _override_get_session
    return application


@pytest_asyncio.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


async def _create_user(session_factory, email: str, role: RoleEnum) -> None:
    async with session_factory() as session:
        session.add(User(email=email, password_hash=hash_password(PASSWORD), full_name=email.split("@")[0], role=role))
        await session.commit()


async def _auth_headers(client: AsyncClient, email: str) -> dict:
    response = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest_asyncio.fixture
async def admin_headers(client, session_factory) -> dict:
    await _create_user(session_factory, "admin@example.com", RoleEnum.ADMIN)
    return await _auth_headers(client, "admin@example.com")


@pytest_asyncio.fixture
async def operator_headers(client, session_factory) -> dict:
    await _create_user(session_factory, "operator@example.com", RoleEnum.OPERATOR)
    return await _auth_headers(client, "operator@example.com")
