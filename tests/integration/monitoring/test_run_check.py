import httpx
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitoring.enums import CheckStatus, ErrorType
from app.modules.monitoring.models import Service
from app.modules.monitoring.repository import CheckResultRepository
from app.modules.monitoring.service import MonitoringService


async def test_run_check_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """Проверяет run_check -> 200."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    service_id = response.json()["id"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        monitoring_service = MonitoringService(db_session)
        result = await monitoring_service.run_check(service_id, client=mock_http)

    assert result is not None
    assert result.status == CheckStatus.UP
    assert result.status_code == 200

    check_repo = CheckResultRepository(db_session)
    latest = await check_repo.get_latest(service_id)
    assert latest is not None
    assert latest.id == result.id

    service = await db_session.get(Service, service_id)
    assert service is not None
    await db_session.refresh(service)
    assert service.current_status == CheckStatus.UP
    assert service.last_check_at is not None


async def test_run_check_timeout(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """Проверяет run_check -> TimeoutException."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    service_id = response.json()["id"]

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timeout")

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        monitoring_service = MonitoringService(db_session)
        result = await monitoring_service.run_check(service_id, client=mock_http)

    assert result is not None
    assert result.status == CheckStatus.DOWN
    assert result.error_type == ErrorType.TIMEOUT

    check_repo = CheckResultRepository(db_session)
    latest = await check_repo.get_latest(service_id)
    assert latest is not None
    assert latest.id == result.id

    service = await db_session.get(Service, service_id)
    assert service is not None
    await db_session.refresh(service)
    assert service.current_status == CheckStatus.DOWN


async def test_run_check_http_error_500(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """Проверяет run_check -> 500."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    service_id = response.json()["id"]

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        monitoring_service = MonitoringService(db_session)
        result = await monitoring_service.run_check(service_id, client=mock_http)

    assert result is not None
    assert result.status == CheckStatus.DOWN
    assert result.error_type == ErrorType.HTTP_ERROR

    service = await db_session.get(Service, service_id)
    assert service is not None
    await db_session.refresh(service)
    assert service.current_status == CheckStatus.DOWN


async def test_run_check_service_not_found(db_session: AsyncSession) -> None:
    """Проверяет несуществующий service_id."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        monitoring_service = MonitoringService(db_session)
        result = await monitoring_service.run_check(999_999_999, client=mock_http)

    assert result is None

    check_repo = CheckResultRepository(db_session)
    latest = await check_repo.get_latest(999_999_999)
    assert latest is None


async def test_run_check_inactive_service(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """Проверяет service с is_active=False."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    service_id = response.json()["id"]

    patch_resp = await client.patch(
        f"/services/{service_id}", json={"is_active": False}, headers=auth_headers
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        monitoring_service = MonitoringService(db_session)
        result = await monitoring_service.run_check(service_id, client=mock_http)

    assert result is None

    service = await db_session.get(Service, service_id)
    assert service is not None
    assert service.is_active is False


async def test_run_check_updates_last_check_at(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """Проверяет: до проверки last_check_at=None, после — не None."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    service_id = response.json()["id"]

    service = await db_session.get(Service, service_id)
    assert service is not None
    assert service.last_check_at is None

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        monitoring_service = MonitoringService(db_session)
        await monitoring_service.run_check(service_id, client=mock_http)

    assert service.last_check_at is not None

    check_repo = CheckResultRepository(db_session)
    latest = await check_repo.get_latest(service_id)
    assert latest is not None
    assert latest.checked_at == service.last_check_at
