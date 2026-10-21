from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import NullPool, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.database import Base
from app.core.dependencies import get_db_session
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


@pytest.fixture
async def db_session() -> AsyncIterator[AsyncSession]:
    """Сессия для прямого доступа к тестовой БД с очисткой перед тестом."""

    async with test_session_factory() as session:
        await session.execute(text("TRUNCATE users RESTART IDENTITY CASCADE"))
        await session.commit()
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
