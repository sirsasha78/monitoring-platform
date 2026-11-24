import asyncio
import json
import logging
import signal
from contextlib import suppress

from aio_pika import ExchangeType, Message, connect_robust
from aio_pika.abc import AbstractExchange
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import *  # noqa: F403
from app.modules.notifications.repository import OutboxRepository

logger = logging.getLogger(__name__)

_running = True

_shutdown_event = asyncio.Event()


def _handle_signal(signum: int, _frame: object) -> None:
    """Вызывается, когда ОС шлёт SIGTERM/SIGINT."""

    global _running
    logger.info("Получен сигнал %s, корректное завершение работы...", signum)
    _running = False
    _shutdown_event.set()


async def publish_batch(session: AsyncSession, exchange: AbstractExchange) -> int:
    """Публикует батч неопубликованных outbox-сообщений в RMQ. publish → mark_published;
    при ошибке — attempts++, last_error. Один commit на батч. Возвращает число обработанных."""

    repo = OutboxRepository(session)
    messages = await repo.get_unpublished(limit=settings.outbox_publisher_batch_size)

    for msg in messages:
        try:
            await exchange.publish(
                Message(body=json.dumps(msg.payload).encode()), routing_key=msg.event_type
            )
            await repo.mark_published(msg)
        except Exception as e:
            msg.attempts += 1
            msg.last_error = str(e)[:500]
            if msg.attempts > 5:
                logger.warning(
                    "Outbox message %s (event_type=%s) failed %d times: %s",
                    msg.id,
                    msg.event_type,
                    msg.attempts,
                    msg.last_error,
                )

    await session.commit()

    return len(messages)


async def main() -> None:
    """Точка входа для outbox publisher."""

    global _running
    _running = True
    _shutdown_event.clear()

    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.getLogger("aio_pika").setLevel(logging.WARNING)
    logging.getLogger("aiormq").setLevel(logging.WARNING)
    logging.getLogger("redis.asyncio.connection").setLevel(logging.WARNING)

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, _handle_signal, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, _handle_signal, signal.SIGINT, None)
    logger.info("Outbox publisher запускается...")

    async with Redis.from_url(url=settings.redis_url) as redis:
        lock = redis.lock("outbox_publisher:lock", timeout=settings.outbox_publisher_lock_ttl)
        acquired = await lock.acquire(blocking=False)

        if not acquired:
            logger.info("Блокировка занята другим publisher'ом, выхожу")
            return

        logger.info("Блокировка получена, начинаю цикл публикации")
        try:
            connection = await connect_robust(settings.rabbitmq_url)

            async with connection:
                channel = await connection.channel()
                exchange = await channel.declare_exchange(
                    settings.rabbitmq_exchange, ExchangeType.TOPIC, durable=True
                )

                while _running:
                    async with SessionLocal() as session:
                        try:
                            await publish_batch(session, exchange)
                        except Exception:
                            logger.exception("Ошибка батча публикации")

                    with suppress(TimeoutError):
                        await asyncio.wait_for(
                            _shutdown_event.wait(),
                            timeout=settings.outbox_publisher_sleep_seconds,
                        )
        finally:
            try:
                await lock.release()
            except Exception as e:
                logger.warning("Не удалось освободить блокировку: %s", e)

    logger.info("Outbox publisher корректно завершил работу")


if __name__ == "__main__":
    asyncio.run(main())
