from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident
from app.modules.incidents.service import IncidentService
from app.modules.monitoring.enums import CheckStatus, ErrorType
from app.modules.monitoring.models import CheckResult, Service
from app.modules.notifications.models import OutboxMessage


async def test_process_check_creates_outbox_on_open(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """Открытие инцидента → создан OutboxMessage(incident.opened, dedup_key, payload)."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_failures=2,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.DOWN,
        checked_at=datetime.now(UTC),
        error_type=ErrorType.TIMEOUT,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)

    assert result is not None
    assert result.status == IncidentStatus.OPEN
    assert result.service_id == service.id
    assert result.trigger_error_type == ErrorType.TIMEOUT
    assert result.started_at == check_result.checked_at

    assert service.consecutive_failures == 0

    outbox_messages = await db_session.scalars(select(OutboxMessage))
    outbox_messages = outbox_messages.all()
    assert len(outbox_messages) == 1

    msg = outbox_messages[0]

    assert msg.event_type == "incident.opened"
    assert msg.payload["incident_id"] == result.id
    assert msg.payload["service_id"] == service.id
    assert msg.deduplication_key == f"incident.opened:{result.id}"
    assert msg.published_at is None
    assert msg.attempts == 0


async def test_process_check_creates_outbox_on_resolve(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """Закрытие инцидента → OutboxMessage(incident.resolved) с тем же incident_id."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_successes=1,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    incident = Incident(
        service_id=service.id,
        started_at=datetime.now(UTC) - timedelta(seconds=400),
        status=IncidentStatus.OPEN,
        trigger_error_type=ErrorType.TIMEOUT,
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.UP,
        checked_at=datetime.now(UTC),
        error_type=None,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)

    assert result is not None
    assert result.id == incident.id
    assert result.status == IncidentStatus.RESOLVED
    assert result.resolved_at == check_result.checked_at

    outbox_messages = await db_session.scalars(select(OutboxMessage))
    outbox_messages = outbox_messages.all()
    assert len(outbox_messages) == 1

    msg = outbox_messages[0]

    assert msg.event_type == "incident.resolved"
    assert msg.payload["incident_id"] == incident.id
    assert msg.payload["service_id"] == service.id
    assert msg.deduplication_key == f"incident.resolved:{incident.id}"


async def test_process_check_no_outbox_on_no_transition(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """DOWN до порога → failures растёт, инцидента нет, OutboxMessage не создан."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        consecutive_failures=0,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.DOWN,
        checked_at=datetime.now(UTC),
        error_type=ErrorType.TIMEOUT,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)

    assert result is None
    assert service.consecutive_failures == 1

    outbox_messages = await db_session.scalars(select(OutboxMessage))
    outbox_messages = outbox_messages.all()
    assert len(outbox_messages) == 0

    stmt = select(Incident).where(Incident.service_id == service.id)
    result_inc = await db_session.scalars(stmt)
    assert result_inc.first() is None


async def test_process_check_no_outbox_on_existing_incident(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """DOWN на уже открытом инциденте → нет перехода, дубль OutboxMessage не создаётся."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        consecutive_failures=2,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    incident = Incident(
        service_id=service.id,
        started_at=datetime.now(UTC) - timedelta(seconds=400),
        status=IncidentStatus.OPEN,
        trigger_error_type=ErrorType.TIMEOUT,
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.DOWN,
        checked_at=datetime.now(UTC),
        error_type=ErrorType.TIMEOUT,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)

    assert result is None
    assert service.consecutive_failures == 3

    outbox_messages = await db_session.scalars(select(OutboxMessage))
    outbox_messages = outbox_messages.all()
    assert len(outbox_messages) == 0

    assert incident.status == IncidentStatus.OPEN
    assert incident.resolved_at is None
