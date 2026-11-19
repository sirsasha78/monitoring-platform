from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.incidents.models import Incident
from app.modules.notifications.models import OutboxMessage
from app.modules.notifications.repository import OutboxRepository


class OutboxService:
    """Сервисный класс для outbox."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = OutboxRepository(session)

    async def publish_incident_event(self, event_type: str, incident: Incident) -> OutboxMessage:
        """Создаёт OutboxMessage для события инцидента (без commit, атомарно с process_check)."""

        deduplication_key = f"{event_type}:{incident.id}"
        payload: dict[str, object] = {
            "incident_id": incident.id,
            "service_id": incident.service_id,
        }
        message = OutboxMessage(
            event_type=event_type,
            payload=payload,
            deduplication_key=deduplication_key,
        )

        return await self._repo.add(message)
