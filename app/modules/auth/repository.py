from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


class UserRepository:
    """Класс репозитория для пользователей."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, user_id: int) -> User | None:
        """Метод для получения пользователя по ID."""

        user = await self._session.get(User, user_id)

        return user

    async def get_by_email(self, email: str) -> User | None:
        """Метод для получения пользователя по email."""

        stmt = select(User).where(User.email == email)
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        """Метод для получения пользователя по username."""

        stmt = select(User).where(User.username == username)
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none()

    async def exists_by_email(self, email: str) -> bool:
        """Метод для проверки существования пользователя по email."""

        stmt = select(User.id).where(User.email == email).limit(1)
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none() is not None

    async def exists_by_username(self, username: str) -> bool:
        """Метод для проверки существования пользователя по username."""

        stmt = select(User.id).where(User.username == username).limit(1)
        result = await self._session.execute(stmt)

        return result.scalar_one_or_none() is not None

    async def add(self, user: User) -> User:
        """Метод для добавления пользователя."""

        self._session.add(user)
        await self._session.flush()

        return user
