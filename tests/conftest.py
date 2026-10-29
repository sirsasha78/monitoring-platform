from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.core.dependencies import get_db_session
from app.core.security import create_access_token
from app.main import app
from app.models import *  # noqa: F403

TEST_DATABASE_URL = (
    f"postgresql+asyncpg://{settings.postgres_user}:{settings.postgres_password}"
    f"@{settings.postgres_host}:{settings.postgres_port}/monitoring_test"
)

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
test_session_factory = async_sessionmaker(bind=test_engine, expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
async def setup_db() -> None:
    """Создаёт все таблицы в тестовой БД перед сессией тестов."""

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@pytest.fixture(autouse=True)
async def _clean_db() -> AsyncIterator[None]:
    """Очищает таблицы перед каждым тестом для изоляции."""

    async with test_session_factory() as session:
        await session.execute(text("TRUNCATE users, services RESTART IDENTITY CASCADE"))
        await session.commit()
    yield


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Сессия для прямого доступа к тестовой БД с очисткой перед тестом."""

    async with test_session_factory() as session:
        yield session


async def _override_get_db_session() -> AsyncIterator[AsyncSession]:
    """Override для get_db_session — использует тестовую БД."""

    async with test_session_factory() as session:
        yield session


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    """HTTP-клиент с подменённой БД."""

    app.dependency_overrides[get_db_session] = _override_get_db_session

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            yield c
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def user_data() -> dict[str, str]:
    """Валидные данные для регистрации нового пользователя."""

    return {
        "username": "alice_92",
        "email": "alice@example.com",
        "password": "secret123",
    }


@pytest.fixture
async def registered_user(client: AsyncClient, user_data: dict[str, str]) -> dict[str, str]:
    """Создаёт пользователя через API. Возвращает user_data + id."""

    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    return {**user_data, "id": response.json()["id"]}


@pytest.fixture
async def auth_token(registered_user: dict[str, str]) -> str:
    """Создает access token для registered_user."""

    return create_access_token(registered_user["id"])


@pytest.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Добавляет заголовки."""

    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
async def second_user(client: AsyncClient) -> dict[str, str]:
    """Создает второго пользователя для тестирования."""

    data = {"username": "smoke_bob", "email": "bob@smoke.com", "password": "secret123"}
    response = await client.post("/auth/register", json=data)
    assert response.status_code == 201
    return {**data, "id": response.json()["id"]}


@pytest.fixture
async def second_user_headers(second_user: dict[str, str]) -> dict[str, str]:
    """Добавляет заголовок второму пользователю."""

    token = create_access_token(second_user["id"])
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def service_data() -> dict[str, object]:
    """Валидные данные для создания нового сервиса."""

    return {
        "name": "Stripe",
        "url": "https://api.stripe.com/health",
        "interval_seconds": 30,
    }
