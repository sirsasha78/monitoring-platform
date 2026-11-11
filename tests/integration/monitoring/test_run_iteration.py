import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.monitoring.enums import CheckStatus
from app.modules.monitoring.models import Service
from app.workers.scheduler import run_iteration


async def test_run_iteration_checks_all_due(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """2 due-сервиса → checked=2, оба current_status=UP."""

    service1 = Service(
        user_id=user_for_services.id,
        name="s1",
        url="https://a.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=True,
    )
    service2 = Service(
        user_id=user_for_services.id,
        name="s2",
        url="https://b.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=True,
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        checked = await run_iteration(db_session, client=mock_http)

    assert checked == 2

    await db_session.refresh(service1)
    await db_session.refresh(service2)

    assert service1.current_status == CheckStatus.UP
    assert service2.current_status == CheckStatus.UP


async def test_run_iteration_no_due_services(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """Нет due-сервисов → checked=0."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        checked = await run_iteration(db_session, client=mock_http)

    assert checked == 0


async def test_run_iteration_passes_client(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """client проброшен в run_check (handler вызван)."""

    service = Service(
        user_id=user_for_services.id,
        name="s",
        url="https://a.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()

    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(str(request.url))
        return httpx.Response(200)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        checked = await run_iteration(db_session, client=mock_http)

    assert checked == 1
    assert len(captured) == 1
    assert "a.com" in captured[0]


async def test_run_iteration_skips_down_service(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """500 → checked=1 (DOWN тоже проверен)."""

    service = Service(
        user_id=user_for_services.id,
        name="s",
        url="https://a.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock_http:
        checked = await run_iteration(db_session, client=mock_http)

    assert checked == 1

    await db_session.refresh(service)
    assert service.current_status == CheckStatus.DOWN
