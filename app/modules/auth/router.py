from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm

from app.modules.auth.dependencies import AuthServiceDep, CurrentUserDep
from app.modules.auth.models import User
from app.modules.auth.schemas import Token, UserRead, UserRegister

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(data: UserRegister, service: AuthServiceDep) -> UserRead:
    """Регистрирует нового пользователя."""

    user = await service.register(data)
    return UserRead.model_validate(user)


@router.post("/login", response_model=Token)
async def login(
    form: Annotated[OAuth2PasswordRequestForm, Depends()], service: AuthServiceDep
) -> Token:
    """Аутентифицирует пользователя и выдаёт access token.
    По стандарту OAuth2: передайте `username` (ваш email) и `password`
    в формате `application/x-www-form-urlencoded`."""

    access_token = await service.login(form.username, form.password)
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
async def me(current_user: CurrentUserDep) -> User:
    """Возвращает текущего пользователя"""

    return current_user
