import time
from datetime import UTC, datetime

import httpx
from httpx import AsyncClient

from app.modules.monitoring.enums import CheckStatus, ErrorType
from app.modules.monitoring.models import CheckResult, Service


async def check_service(service: Service, client: AsyncClient | None = None) -> CheckResult:
    """Функция для проверки сервиса."""

    own_client = client is None
    actual_client: AsyncClient = client if client is not None else AsyncClient()

    try:
        start = time.perf_counter()
        status_code: int | None = None
        error_type: ErrorType | None = None
        error_message: str | None = None
        status = CheckStatus.DOWN
        try:
            response = await actual_client.request(
                service.method, service.url, timeout=service.timeout_seconds
            )
            status_code = response.status_code
            if 200 <= status_code < 300:
                status = CheckStatus.UP
            else:
                error_type = ErrorType.HTTP_ERROR

        except httpx.TimeoutException as e:
            error_type = ErrorType.TIMEOUT
            error_message = str(e)
        except httpx.ConnectError as e:
            msg = str(e)
            if "[SSL:" in msg:
                error_type = ErrorType.SSL_ERROR
            elif "Name or service not known" in msg:
                error_type = ErrorType.DNS_ERROR
            else:
                error_type = ErrorType.CONNECTION_ERROR
            error_message = msg
        except httpx.RequestError as e:
            error_type = ErrorType.CONNECTION_ERROR
            error_message = str(e)
        finally:
            latency_ms = int((time.perf_counter() - start) * 1000)

        return CheckResult(
            service_id=service.id,
            checked_at=datetime.now(UTC),
            status=status,
            status_code=status_code,
            latency_ms=latency_ms,
            error_type=error_type,
            error_message=error_message,
        )
    finally:
        if own_client:
            await actual_client.aclose()
