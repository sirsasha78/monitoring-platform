from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.monitoring.models import CheckResult, Service


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


class CheckResultRepository:
    """Класс репозитория для CheckResult."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, check_result: CheckResult) -> CheckResult:
        """Метод для добавления CheckResult."""

        self._session.add(check_result)
        await self._session.flush()

        return check_result

    async def get_latest(self, service_id: int) -> CheckResult | None:
        """Возвращает последний чек сервиса."""

        result = await self._session.scalars(
            select(CheckResult)
            .where(CheckResult.service_id == service_id)
            .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
            .limit(1)
        )

        return result.first()

    async def list_recent(self, service_id: int, limit: int = 10) -> list[CheckResult]:
        """Возвращает последние N чеков, новые сверху."""

        result = await self._session.scalars(
            select(CheckResult)
            .where(CheckResult.service_id == service_id)
            .order_by(CheckResult.checked_at.desc(), CheckResult.id.desc())
            .limit(limit)
        )

        return list(result.all())
