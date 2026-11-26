from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident
from app.modules.monitoring.models import Service


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

    async def list_by_user_id(
        self, user_id: int, limit: int = 50, offset: int = 0, status: IncidentStatus | None = None
    ) -> list[Incident]:
        """Список инцидентов пользователя (через JOIN с Service), новые сверху."""

        stmt = select(Incident).join(Service).where(Service.user_id == user_id)

        if status is not None:
            stmt = stmt.where(Incident.status == status)

        stmt = (
            stmt.order_by(Incident.started_at.desc(), Incident.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(stmt)

        return list(result.all())

    async def list_by_service_id(
        self,
        service_id: int,
        limit: int = 50,
        offset: int = 0,
        status: IncidentStatus | None = None,
    ) -> list[Incident]:
        """Список инцидентов сервиса, новые сверху. Владелец проверяется в роутере."""

        stmt = select(Incident).where(Incident.service_id == service_id)

        if status is not None:
            stmt = stmt.where(Incident.status == status)

        stmt = (
            stmt.order_by(Incident.started_at.desc(), Incident.id.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await self._session.scalars(stmt)

        return list(result.all())

    async def get_for_user(self, user_id: int, incident_id: int) -> Incident | None:
        """Инцидент по id, только если принадлежит пользователю (через JOIN). Иначе None."""

        stmt = (
            select(Incident)
            .join(Service)
            .where(Incident.id == incident_id, Service.user_id == user_id)
            .limit(1)
        )
        result = await self._session.scalars(stmt)

        return result.first()

    async def get_with_relations(self, incident_id: int) -> Incident | None:
        """Инцидент с eager-loaded service и service.user (для consumer'а)."""

        stmt = (
            select(Incident)
            .options(joinedload(Incident.service).joinedload(Service.user))
            .where(Incident.id == incident_id)
        )
        result = await self._session.scalars(stmt)

        return result.unique().first()
