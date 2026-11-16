from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.modules.incidents.exceptions import IncidentNotFoundError, IncidentsError

_INCIDENTS_ERROR_STATUS: dict[type[IncidentsError], int] = {IncidentNotFoundError: 404}


def incidents_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Превращает бизнес-исключения incident в HTTP-ответы."""

    if not isinstance(exc, IncidentsError):
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    status_code = _INCIDENTS_ERROR_STATUS.get(type(exc), 500)

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
    )


def register_incidents_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений incident в приложении."""

    for error_cls in _INCIDENTS_ERROR_STATUS:
        app.add_exception_handler(error_cls, incidents_error_handler)
