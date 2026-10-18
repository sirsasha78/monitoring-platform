from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DBSessionDep
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.auth.exceptions import (
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository
from app.modules.auth.schemas import UserRegister

_DUMMY_PASSWORD_HASH = hash_password("dummy-password-for-timing-protection")


class AuthService:
    """Сервис аутентификации: регистрация и логин."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = UserRepository(session)

    async def register(self, data: UserRegister) -> User:
        """Регистрирует нового пользователя."""

        if await self._repo.exists_by_email(data.email):
            raise EmailAlreadyExistsError("Пользователь с таким email уже существует.")
        if await self._repo.exists_by_username(data.username):
            raise UsernameAlreadyExistsError("Пользователь с таким именем уже существует.")

        password_hash = hash_password(data.password)
        user = User(username=data.username, email=data.email, password_hash=password_hash)

        await self._repo.add(user)
        await self._session.commit()
        await self._session.refresh(user)

        return user

    async def login(self, email: str, password: str) -> str:
        """Аутентифицирует пользователя и возвращает access token."""

        user = await self._repo.get_by_email(email)

        if user is None:
            verify_password(password, _DUMMY_PASSWORD_HASH)
            raise InvalidCredentialsError("Неверный email или пароль.")

        if not verify_password(password, user.password_hash):
            raise InvalidCredentialsError("Неверный email или пароль.")

        if not user.is_active:
            raise InactiveUserError("Пользователь не активен.")

        return create_access_token(user.id)


def get_auth_service(session: DBSessionDep) -> AuthService:
    """Создаёт AuthService с переданной сессией."""

    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
