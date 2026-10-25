from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitoring.models import Service


class ServiceRepository:
    """Класс репозитория для сервисов."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, service_id: int) -> Service | None:
        """Метод для получения сервиса по ID."""

        service = await self._session.get(Service, service_id)

        return service

    async def list_by_user_id(self, user_id: int) -> list[Service]:
        """Метод для получения всех сервисов пользователя."""

        result = await self._session.scalars(
            select(Service).where(Service.user_id == user_id).order_by(Service.created_at.desc())
        )

        return list(result.all())

    async def add(self, service: Service) -> Service:
        """Метод для добавления сервиса."""

        self._session.add(service)
        await self._session.flush()

        return service

    async def delete(self, service: Service) -> None:
        """Метод для удаления сервиса."""

        await self._session.delete(service)
