from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident


class IncidentRepository:
    """Класс репозитория для инцидентов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_open_by_service_id(self, service_id: int) -> Incident | None:
        """Метод для получения открытого инцидента сервиса (status=open)."""

        stmt = (
            select(Incident)
            .where(Incident.service_id == service_id, Incident.status == IncidentStatus.OPEN)
            .limit(1)
        )
        result = await self._session.scalars(stmt)

        return result.first()

    async def add(self, incident: Incident) -> Incident:
        """Метод для добавления инцидента."""

        self._session.add(incident)
        await self._session.flush()

        return incident
