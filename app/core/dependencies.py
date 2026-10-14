from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import SessionLocal


async def get_db_session() -> AsyncGenerator[AsyncSession]:
    """Предоставляет асинхронную сессию SQLAlchemy для работы с базой данных PostgreSQL."""

    async with SessionLocal() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db_session)]
