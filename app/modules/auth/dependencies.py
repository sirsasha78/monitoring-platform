from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from app.core.dependencies import DBSessionDep
from app.core.security import decode_access_token
from app.modules.auth.exceptions import InactiveUserError, InvalidTokenError
from app.modules.auth.models import User
from app.modules.auth.service import AuthService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)], session: DBSessionDep
) -> User:
    """Проверяет JWT и возвращает пользователя из базы."""

    credentials_exception = InvalidTokenError("Невалидный или истёкший токен.")

    try:
        payload = decode_access_token(token)
        sub = payload.get("sub")
        if sub is None:
            raise credentials_exception
        sub = int(sub)
    except jwt.InvalidTokenError, ValueError:
        raise credentials_exception from None

    user = await session.get(User, sub)
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise InactiveUserError("Пользователь не активен.")

    return user


CurrentUserDep = Annotated[User, Depends(get_current_user)]


def get_auth_service(session: DBSessionDep) -> AuthService:
    """Создаёт AuthService с переданной сессией."""

    return AuthService(session)


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
