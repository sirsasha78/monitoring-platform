from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.modules.monitoring.exceptions import MonitoringError, ServiceNotFoundError

_MONITORING_ERROR_STATUS: dict[type[MonitoringError], int] = {ServiceNotFoundError: 404}


def monitoring_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Превращает бизнес-исключения monitoring в HTTP-ответы."""

    if not isinstance(exc, MonitoringError):
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

    status_code = _MONITORING_ERROR_STATUS.get(type(exc), 500)

    return JSONResponse(
        status_code=status_code,
        content={"detail": str(exc)},
    )


def register_monitoring_exception_handlers(app: FastAPI) -> None:
    """Регистрирует обработчики исключений monitoring в приложении."""

    for error_cls in _MONITORING_ERROR_STATUS:
        app.add_exception_handler(error_cls, monitoring_error_handler)
