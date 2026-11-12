from datetime import timedelta
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import DBSessionDep
from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident
from app.modules.incidents.repository import IncidentRepository
from app.modules.monitoring.enums import CheckStatus
from app.modules.monitoring.models import CheckResult, Service


class IncidentService:
    """Класс сервиса для инцидентов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = IncidentRepository(session)

    async def process_check(self, service: Service, check_result: CheckResult) -> Incident | None:
        """Обновляет счётчики, открывает/закрывает инцидент по порогам.
        Возвращает созданный/закрытый Incident или None.
        """

        if check_result.status == CheckStatus.UNKNOWN:
            return None
        if check_result.status == CheckStatus.DOWN:
            service.consecutive_failures += 1
            service.consecutive_successes = 0
        if check_result.status == CheckStatus.UP:
            service.consecutive_successes += 1
            service.consecutive_failures = 0

        open_incident = await self._repo.get_open_by_service_id(service.id)
        result: Incident | None = None

        if open_incident is None and service.consecutive_failures >= service.failure_threshold:
            incident = Incident(
                service_id=service.id,
                started_at=check_result.checked_at,
                status=IncidentStatus.OPEN,
                trigger_error_type=check_result.error_type,
            )
            await self._repo.add(incident)
            service.consecutive_failures = 0
            result = incident
        elif open_incident is not None:
            if service.consecutive_successes >= service.recovery_threshold:
                min_duration = timedelta(seconds=settings.incident_min_duration_seconds)
                if check_result.checked_at - open_incident.started_at >= min_duration:
                    open_incident.resolved_at = check_result.checked_at
                    open_incident.status = IncidentStatus.RESOLVED
                    result = open_incident

        await self._session.commit()

        return result


def get_incident_service(session: DBSessionDep) -> IncidentService:
    """Создаёт IncidentService с переданной сессией."""

    return IncidentService(session)


IncidentServiceDep = Annotated[IncidentService, Depends(get_incident_service)]
