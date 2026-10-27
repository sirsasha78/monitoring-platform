from typing import Annotated

from fastapi import Depends
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DBSessionDep
from app.modules.monitoring.exceptions import ServiceNotFoundError
from app.modules.monitoring.models import Service
from app.modules.monitoring.repository import ServiceRepository
from app.modules.monitoring.schemas import ServiceCreate, ServiceUpdate


class MonitoringService:
    """Класс для управления бизнес логикой сервисов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ServiceRepository(session)

    async def create(self, user_id: int, data: ServiceCreate) -> Service:
        """Создает новый сервис."""

        service = Service(user_id=user_id, **data.model_dump(mode="json"))
        await self._repo.add(service)
        await self._session.commit()
        await self._session.refresh(service)

        return service

    async def list_for_user(self, user_id: int) -> list[Service]:
        """Возвращает все сервисы пользователя (включая на паузе), новые сверху."""

        return await self._repo.list_by_user_id(user_id)

    async def get_for_user(self, user_id: int, service_id: int) -> Service:
        """Возвращает сервис по ID."""

        service = await self._repo.get_by_id(service_id)

        if service is None or service.user_id != user_id:
            raise ServiceNotFoundError("Сервис не найден.")

        return service

    async def update(self, user_id: int, service_id: int, data: ServiceUpdate) -> Service:
        """Обновляет сервис."""

        service = await self.get_for_user(user_id, service_id)
        await self._session.execute(
            update(Service)
            .where(Service.id == service.id)
            .values(**data.model_dump(exclude_unset=True, mode="json"))
        )

        await self._session.commit()
        await self._session.refresh(service)

        return service

    async def delete(self, user_id: int, service_id: int) -> None:
        """Удаляет сервис."""

        service = await self.get_for_user(user_id, service_id)
        await self._repo.delete(service)
        await self._session.commit()


def get_monitoring_service(session: DBSessionDep) -> MonitoringService:
    """Создаёт MonitoringService с переданной сессией."""

    return MonitoringService(session)


MonitoringServiceDep = Annotated[MonitoringService, Depends(get_monitoring_service)]
