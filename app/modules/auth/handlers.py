from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.modules.auth.exceptions import (
    AuthError,
    EmailAlreadyExistsError,
    InactiveUserError,
    InvalidCredentialsError,
    InvalidTokenError,
    UsernameAlreadyExistsError,
)

_AUTH_ERROR_STATUS: dict[type[AuthError], int] = {
    EmailAlreadyExistsError: 409,
    UsernameAlreadyExistsError: 409,
    InvalidCredentialsError: 401,
    InactiveUserError: 403,
    InvalidTokenError: 401,
}


async def auth_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Превращает бизнес-исключения auth в HTTP-ответы."""

    if not isinstance(exc, AuthError):
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    status_code = _AUTH_ERROR_STATUS.get(type(exc), 500)
    headers = {"WWW-Authenticate": "Bearer"} if status_code == 401 else {}

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
        headers=headers,
    )


def register_auth_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений auth в приложении."""

    for error_cls in _AUTH_ERROR_STATUS:
        app.add_exception_handler(error_cls, auth_error_handler)
