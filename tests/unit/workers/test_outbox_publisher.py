from typing import Any
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import OutboxMessage
from app.workers.outbox_publisher import publish_batch


@pytest.fixture
def exchange() -> Any:
    """Mock AbstractExchange для тестов publish_batch (успех по умолчанию)."""

    mock = AsyncMock()
    mock.publish = AsyncMock()

    return mock


async def test_publish_batch_marks_published(db_session: AsyncSession, exchange: Any) -> None:
    """2 сообщения, publish успешен → published_at заполнены, attempts=0, return 2."""

    msg1 = OutboxMessage(
        event_type="incident.opened",
        payload={"incident_id": 1, "service_id": 1},
        deduplication_key="incident.opened:1",
    )
    msg2 = OutboxMessage(
        event_type="incident.resolved",
        payload={"incident_id": 2, "service_id": 2},
        deduplication_key="incident.resolved:2",
    )
    db_session.add_all([msg1, msg2])
    await db_session.commit()
    await db_session.refresh(msg1)
    await db_session.refresh(msg2)

    count = await publish_batch(db_session, exchange)

    assert count == 2
    assert exchange.publish.await_count == 2

    await db_session.refresh(msg1)
    await db_session.refresh(msg2)

    assert msg1.published_at is not None
    assert msg2.published_at is not None
    assert msg1.attempts == 0
    assert msg2.attempts == 0
    assert msg1.last_error is None
    assert msg2.last_error is None


async def test_publish_batch_attempts_on_failure(db_session: AsyncSession, exchange: Any) -> None:
    """1 сообщение, publish бросает Exception → published_at=None,
    attempts=1, last_error сохранён.
    """

    exchange.publish.side_effect = Exception("RMQ down")

    msg = OutboxMessage(
        event_type="incident.opened",
        payload={"incident_id": 1, "service_id": 1},
        deduplication_key="incident.opened:1",
    )
    db_session.add(msg)
    await db_session.commit()
    await db_session.refresh(msg)

    count = await publish_batch(db_session, exchange)
    assert count == 1

    await db_session.refresh(msg)

    assert msg.published_at is None
    assert msg.attempts == 1
    assert msg.last_error == "RMQ down"


async def test_publish_batch_partial_failure(db_session: AsyncSession, exchange: Any) -> None:
    """2 сообщения, первый publish упал, второй успех → attempts=1/0,
    второй published_at заполнен.
    """

    exchange.publish.side_effect = [Exception("RMQ down"), None]

    msg1 = OutboxMessage(
        event_type="incident.opened",
        payload={"incident_id": 1, "service_id": 1},
        deduplication_key="incident.opened:1",
    )
    msg2 = OutboxMessage(
        event_type="incident.resolved",
        payload={"incident_id": 2, "service_id": 2},
        deduplication_key="incident.resolved:2",
    )
    db_session.add_all([msg1, msg2])
    await db_session.commit()
    await db_session.refresh(msg1)
    await db_session.refresh(msg2)

    count = await publish_batch(db_session, exchange)
    assert count == 2
    assert exchange.publish.await_count == 2

    await db_session.refresh(msg1)
    await db_session.refresh(msg2)

    assert msg1.published_at is None
    assert msg1.attempts == 1
    assert msg1.last_error == "RMQ down"
    assert msg2.published_at is not None
    assert msg2.attempts == 0


async def test_publish_batch_no_messages(db_session: AsyncSession, exchange: Any) -> None:
    """Пустой outbox → return 0, exchange.publish не вызывался."""

    count = await publish_batch(db_session, exchange)
    assert count == 0
    assert exchange.publish.await_count == 0
