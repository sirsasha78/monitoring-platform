import asyncio
import contextlib
import logging
import signal

import httpx
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import SessionLocal
from app.models import *  # noqa: F403
from app.modules.incidents.service import IncidentService
from app.modules.monitoring.repository import ServiceRepository
from app.modules.monitoring.service import MonitoringService

logger = logging.getLogger(__name__)

_running = True

_shutdown_event = asyncio.Event()


def _handle_signal(signum: int, _frame: object) -> None:
    """Вызывается, когда ОС шлёт SIGTERM/SIGINT."""

    global _running
    logger.info("Получен сигнал %s, корректное завершение работы...", signum)
    _running = False
    _shutdown_event.set()


async def run_iteration(session: AsyncSession, client: httpx.AsyncClient | None = None) -> int:
    """Функция для проверки сервисов."""

    repo = ServiceRepository(session)
    monitoring = MonitoringService(session)
    incident_service = IncidentService(session)
    services = await repo.list_due_for_check(limit=settings.scheduler_batch_size)
    checked = 0

    for service in services:
        try:
            check_result = await monitoring.run_check(service.id, client=client)
            if check_result is None:
                continue

            checked += 1
            await incident_service.process_check(service, check_result)
        except Exception:
            logger.exception("Ошибка проверки сервиса service_id=%s", service.id)

    return checked


async def main() -> None:
    """Точка входа для запуска планировщика."""

    global _running
    _running = True
    _shutdown_event.clear()

    logging.basicConfig(
        level=settings.log_level, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("redis.asyncio.connection").setLevel(logging.WARNING)

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, _handle_signal, signal.SIGTERM, None)
    loop.add_signal_handler(signal.SIGINT, _handle_signal, signal.SIGINT, None)
    logger.info("Планировщик запускается...")

    async with Redis.from_url(url=settings.redis_url) as redis:
        lock = redis.lock("scheduler:lock", timeout=settings.scheduler_lock_ttl)
        acquired = await lock.acquire(blocking=False)

        if not acquired:
            logger.info("Блокировка занята другим экземпляром планировщика, выхожу")
            return

        logger.info("Блокировка получена, начинаю цикл проверок")
        try:
            while _running:
                async with SessionLocal() as session:
                    try:
                        checked = await run_iteration(session)
                        if checked > 0:
                            logger.debug("Проверено сервисов: %s", checked)
                    except Exception:
                        logger.exception("Ошибка итерации планировщика")
                with contextlib.suppress(TimeoutError):
                    await asyncio.wait_for(
                        _shutdown_event.wait(), timeout=settings.scheduler_sleep_seconds
                    )
        finally:
            try:
                await lock.release()
            except Exception as e:
                logger.warning("Не удалось освободить блокировку: %s", e)

    logger.info("Планировщик корректно завершил работу")


if __name__ == "__main__":
    asyncio.run(main())
