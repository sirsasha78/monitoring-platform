from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import OutboxMessage


class OutboxRepository:
    """Класс репозитория для outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add(self, message: OutboxMessage) -> OutboxMessage:
        """Добавляет сообщение в outbox (flush, без commit)."""

        self._session.add(message)
        await self._session.flush()

        return message

    async def get_unpublished(self, limit: int = 100) -> list[OutboxMessage]:
        """Неопубликованные сообщения, старые первыми. Использует partial index."""

        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.published_at.is_(None))
            .order_by(OutboxMessage.created_at)
            .limit(limit)
        )
        result = await self._session.scalars(stmt)

        return list(result.all())

    async def mark_published(self, message: OutboxMessage, now: datetime | None = None) -> None:
        """Помечает сообщение опубликованным (без commit)."""

        message.published_at = now or datetime.now(UTC)
