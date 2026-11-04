import httpx

from app.modules.monitoring.checker import check_service
from app.modules.monitoring.enums import CheckStatus, ErrorType
from app.modules.monitoring.models import Service


async def test_check_success_2xx(service: Service) -> None:
    """Проверяет: 2xx → UP, status_code, latency >= 0, error_type None."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.status == CheckStatus.UP
    assert result.status_code == 200
    assert result.error_type is None
    assert result.latency_ms is not None
    assert result.latency_ms >= 0


async def test_check_http_error_500(service: Service) -> None:
    """Проверяет: 500 -> DOWN, status_code, error_type."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.status == CheckStatus.DOWN
    assert result.status_code == 500
    assert result.error_type == ErrorType.HTTP_ERROR


async def test_check_http_error_404(service: Service) -> None:
    """Проверяет: 404 -> DOWN, status_code, error_type."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.status == CheckStatus.DOWN
    assert result.status_code == 404
    assert result.error_type == ErrorType.HTTP_ERROR


async def test_check_timeout(service: Service) -> None:
    """Проверяет check_service при исключении TimeoutException."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.status == CheckStatus.DOWN
    assert result.error_type == ErrorType.TIMEOUT
    assert result.status_code is None
    assert result.error_message is not None
    assert "timeout" in result.error_message


async def test_check_connection_error(service: Service) -> None:
    """Проверяет check_service при исключении ConnectError."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("Connection refused")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.status == CheckStatus.DOWN
    assert result.error_type == ErrorType.CONNECTION_ERROR
    assert result.status_code is None


async def test_check_dns_error(service: Service) -> None:
    """Проверяет error_type -> DNS_ERROR."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[Errno -2] Name or service not known")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.error_type == ErrorType.DNS_ERROR


async def test_check_ssl_error(service: Service) -> None:
    """Проверяет error_type -> SSL_ERROR."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        result = await check_service(service, client)

    assert result.error_type == ErrorType.SSL_ERROR


async def test_check_uses_service_method(service: Service) -> None:
    """Проверяет, что используется service.method."""

    captured_method: str = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal captured_method
        captured_method = request.method
        return httpx.Response(200)

    service.method = "HEAD"

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await check_service(service, client)

    assert captured_method == "HEAD"


async def test_check_does_not_close_external_client(service: Service) -> None:
    """Проверяет, что check_service не закрывает переданный клиент"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        await check_service(service, client)

        result = await check_service(service, client)
        assert result.status == CheckStatus.UP
