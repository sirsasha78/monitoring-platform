from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.monitoring.models import Service
from app.modules.monitoring.repository import ServiceRepository


async def test_never_checked_included(db_session: AsyncSession, user_for_services: User) -> None:
    """Сервис с last_check_at=None попадает в список."""

    service = Service(
        user_id=user_for_services.id,
        name="never",
        url="https://example.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()

    repo = ServiceRepository(db_session)
    result = await repo.list_due_for_check()

    assert len(result) == 1
    assert result[0].id == service.id


async def test_overdue_included(db_session: AsyncSession, user_for_services: User) -> None:
    """Сервис с просроченным last_check_at (interval < elapsed) попадает в список."""

    service = Service(
        user_id=user_for_services.id,
        name="overdue",
        url="https://example.com",
        interval_seconds=60,
        last_check_at=datetime.now(UTC) - timedelta(seconds=120),
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()

    repo = ServiceRepository(db_session)
    result = await repo.list_due_for_check()

    assert len(result) == 1
    assert result[0].id == service.id


async def test_not_due_excluded(db_session: AsyncSession, user_for_services: User) -> None:
    """Проверяет сервис, который не должен быть добавлен в список."""

    service = Service(
        user_id=user_for_services.id,
        name="not-due",
        url="https://example.com",
        interval_seconds=60,
        last_check_at=datetime.now(UTC) - timedelta(seconds=30),
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()

    repo = ServiceRepository(db_session)
    result = await repo.list_due_for_check()

    assert len(result) == 0


async def test_inactive_excluded(db_session: AsyncSession, user_for_services: User) -> None:
    """Сервис с is_active=False не попадает в список."""

    service = Service(
        user_id=user_for_services.id,
        name="inactive",
        url="https://example.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=False,
    )
    db_session.add(service)
    await db_session.commit()

    repo = ServiceRepository(db_session)
    result = await repo.list_due_for_check()

    assert len(result) == 0


async def test_nulls_first_ordering(db_session: AsyncSession, user_for_services: User) -> None:
    """Проверяет сортировку NULLS FIRST."""

    service1 = Service(
        user_id=user_for_services.id,
        name="never1",
        url="https://example.com",
        interval_seconds=60,
        last_check_at=None,
        is_active=True,
    )
    service2 = Service(
        user_id=user_for_services.id,
        name="never2",
        url="https://example.com",
        interval_seconds=60,
        last_check_at=datetime.now(UTC) - timedelta(seconds=120),
        is_active=True,
    )
    db_session.add_all([service1, service2])
    await db_session.commit()

    repo = ServiceRepository(db_session)
    result = await repo.list_due_for_check()

    assert len(result) == 2
    assert result[0].id == service1.id
