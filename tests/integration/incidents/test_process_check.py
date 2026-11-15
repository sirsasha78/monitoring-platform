from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident
from app.modules.incidents.repository import IncidentRepository
from app.modules.incidents.service import IncidentService
from app.modules.monitoring.enums import CheckStatus, ErrorType
from app.modules.monitoring.models import CheckResult, Service


async def test_first_failure_no_incident(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """1-й DOWN при threshold=3 → failures=1, инцидента нет."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
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
    assert service.consecutive_successes == 0

    repo = IncidentRepository(db_session)
    assert await repo.get_open_by_service_id(service.id) is None


async def test_threshold_reached_creates_incident(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """3-й DOWN подряд (failures 2→3 при threshold=3) → инцидент создан, failures сброшен."""

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
    assert result.resolved_at is None
    assert result.started_at == check_result.checked_at

    assert service.consecutive_failures == 0
    assert service.consecutive_successes == 0

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is not None
    assert open_inc.id == result.id


async def test_no_incident_and_up_returns_none(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """UP без открытого инцидента → successes=1, инцидент не создан, None."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.UP,
        checked_at=datetime.now(UTC),
        error_type=None,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)
    assert result is None

    assert service.consecutive_successes == 1
    assert service.consecutive_failures == 0

    repo = IncidentRepository(db_session)
    assert await repo.get_open_by_service_id(service.id) is None


async def test_incident_already_open_no_duplicate(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """DOWN на уже открытом инциденте → второй не создаётся, failures растёт."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    incident = Incident(
        service_id=service.id,
        started_at=datetime.now(UTC) - timedelta(seconds=10),
        status=IncidentStatus.OPEN,
        trigger_error_type=ErrorType.TIMEOUT,
    )
    db_session.add(incident)
    await db_session.commit()

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

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is not None
    assert open_inc.id == incident.id


async def test_incident_already_open_failures_grow(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """Открытый инцидент + DOWN, failures 2→3 → failures=3, инцидент не трогается."""

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

    incident = Incident(
        service_id=service.id,
        started_at=datetime.now(UTC) - timedelta(seconds=10),
        status=IncidentStatus.OPEN,
        trigger_error_type=ErrorType.TIMEOUT,
    )
    db_session.add(incident)
    await db_session.commit()

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
    assert service.consecutive_successes == 0

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is not None
    assert open_inc.id == incident.id


async def test_success_below_recovery(db_session: AsyncSession, user_for_services: User) -> None:
    """UP на открытом инциденте, successes 0→1 < recovery=2 → не закрываем, None."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
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

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.UP,
        checked_at=datetime.now(UTC),
        error_type=None,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)
    assert result is None

    assert service.consecutive_successes == 1
    assert service.consecutive_failures == 0

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is not None
    assert open_inc.status == IncidentStatus.OPEN
    assert open_inc.resolved_at is None


async def test_unknown_status_does_nothing(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """UNKNOWN → счётчики не меняются, инцидент не создаётся/не закрывается, None."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_failures=2,
        consecutive_successes=1,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.UNKNOWN,
        checked_at=datetime.now(UTC),
        error_type=None,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)
    assert result is None

    assert service.consecutive_failures == 2
    assert service.consecutive_successes == 1

    repo = IncidentRepository(db_session)
    assert await repo.get_open_by_service_id(service.id) is None


async def test_recovery_reached_but_min_duration_not_passed(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """successes 1→2 ≥ recovery, но MIN_DURATION не прошло → не закрываем, None."""

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
        started_at=datetime.now(UTC) - timedelta(seconds=60),
        status=IncidentStatus.OPEN,
        trigger_error_type=ErrorType.TIMEOUT,
    )
    db_session.add(incident)
    await db_session.commit()

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.UP,
        checked_at=datetime.now(UTC),
        error_type=None,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)
    assert result is None

    assert service.consecutive_successes == 2
    assert service.consecutive_failures == 0

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is not None
    assert open_inc.status == IncidentStatus.OPEN
    assert open_inc.resolved_at is None


async def test_recovery_reached_and_min_duration_passed(
    db_session: AsyncSession, user_for_services: User
) -> None:
    """successes 1→2 ≥ recovery, MIN_DURATION прошло → инцидент закрыт, resolved_at=checked_at."""

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

    assert service.consecutive_successes == 2

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is None


async def test_up_resets_failures(db_session: AsyncSession, user_for_services: User) -> None:
    """UP при failures=2, нет инцидента → failures=0, successes=1, None."""

    service = Service(
        user_id=user_for_services.id,
        name="test",
        url="https://example.com",
        failure_threshold=3,
        recovery_threshold=2,
        consecutive_failures=2,
        consecutive_successes=0,
        is_active=True,
    )
    db_session.add(service)
    await db_session.commit()
    await db_session.refresh(service)

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.UP,
        checked_at=datetime.now(UTC),
        error_type=None,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)
    assert result is None

    assert service.consecutive_failures == 0
    assert service.consecutive_successes == 1

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is None


async def test_down_resets_successes(db_session: AsyncSession, user_for_services: User) -> None:
    """DOWN на открытом инциденте, successes=1 → successes=0, failures=1, None."""

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

    check_result = CheckResult(
        service_id=service.id,
        status=CheckStatus.DOWN,
        checked_at=datetime.now(UTC),
        error_type=ErrorType.TIMEOUT,
    )

    incident_service = IncidentService(db_session)
    result = await incident_service.process_check(service, check_result)
    assert result is None

    assert service.consecutive_successes == 0
    assert service.consecutive_failures == 1

    repo = IncidentRepository(db_session)
    open_inc = await repo.get_open_by_service_id(service.id)
    assert open_inc is not None
    assert open_inc.status == IncidentStatus.OPEN
