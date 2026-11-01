"""Smoke-тест для UserRepository.

Запуск: uv run python -m scripts.smoke_auth_repository
"""

"""Smoke-тест для CheckResultRepository."""

import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, or_

from app.core.database import SessionLocal
from app.models import *  # noqa: F403
from app.modules.auth.models import User
from app.modules.monitoring.enums import CheckStatus
from app.modules.monitoring.models import CheckResult, Service
from app.modules.monitoring.repository import CheckResultRepository


async def main() -> None:
    async with SessionLocal() as session:
        # 1. Cleanup В НАЧАЛЕ — идемпотентность
        await session.execute(
            delete(User).where(
                or_(User.email.like("%@smoke.test"), User.username.like("smoke_%"))
            )
        )
        await session.commit()

        # 2. Создать user + service
        user = User(username="smoke_cr_user", email="cr@smoke.test", password_hash="fake")
        session.add(user)
        await session.flush()

        service = Service(name="test-service", url="http://example.com", user_id=user.id)
        session.add(service)
        await session.flush()

        # 3. Repository + 3 CheckResult с РАЗНЫМИ checked_at
        repo = CheckResultRepository(session)
        now = datetime.now(UTC)

        cr1 = CheckResult(
            service_id=service.id, checked_at=now - timedelta(minutes=2), status=CheckStatus.UP
        )
        cr2 = CheckResult(
            service_id=service.id, checked_at=now - timedelta(minutes=1), status=CheckStatus.DOWN
        )
        cr3 = CheckResult(service_id=service.id, checked_at=now, status=CheckStatus.UP)
        await repo.add(cr1)
        await repo.add(cr2)
        await repo.add(cr3)
        await session.commit()

        # 4. get_latest → самый новый (cr3)
        latest = await repo.get_latest(service.id)
        assert latest is not None
        assert latest.id == cr3.id

        # 5. list_recent(limit=2) → [cr3, cr2], новые сверху
        recent = await repo.list_recent(service.id, limit=2)
        assert len(recent) == 2
        assert [c.id for c in recent] == [cr3.id, cr2.id]

        # 6. list_recent(limit=10) → 3
        all_recent = await repo.list_recent(service.id, limit=10)
        assert len(all_recent) == 3

        # 7. get_latest(nonexistent) → None
        assert await repo.get_latest(999_999_999) is None

        # 8. Стабильность: два чека с ОДИНАКОВЫМ checked_at
        same_time = now + timedelta(seconds=1)
        cr_a = CheckResult(service_id=service.id, checked_at=same_time, status=CheckStatus.UP)
        cr_b = CheckResult(service_id=service.id, checked_at=same_time, status=CheckStatus.DOWN)
        await repo.add(cr_a)
        await repo.add(cr_b)
        await session.commit()

        latest_stable = await repo.get_latest(service.id)
        assert latest_stable is not None
        assert latest_stable.id == cr_b.id  # ← больший id, благодаря id.desc()

        await session.rollback()
        print("All smoke checks passed")


if __name__ == "__main__":
    asyncio.run(main())
