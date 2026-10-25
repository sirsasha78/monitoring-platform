"""Smoke-тест для UserRepository.

Запуск: uv run python -m scripts.smoke_auth_repository
"""

import asyncio

from app.core.database import SessionLocal
from app.models import *  # noqa: F403
from app.modules.auth.models import User
from app.modules.auth.repository import UserRepository


async def main() -> None:
    # Часть 1: тест repository
    async with SessionLocal() as session:
        repo = UserRepository(session)

        exists_before = await repo.exists_by_email("alice@example.com")
        print("exists before:", exists_before)

        user = User(
            username="alice_92",
            email="alice@example.com",
            password_hash="fake_hash_for_smoke_test",
        )
        created = await repo.add(user)
        print("created id:", created.id)

        found = await repo.get_by_email("alice@example.com")
        print("found:", found)

        exists_after = await repo.exists_by_email("alice@example.com")
        print("exists after:", exists_after)

        not_found = await repo.get_by_email("none@example.com")
        print("not found:", not_found)

        by_username = await repo.get_by_username("alice_92")
        print("by username:", by_username)

        await session.rollback()
        print("rolled back")

    # Часть 2: проверка после rollback — в том же loop!
    async with SessionLocal() as session:
        repo = UserRepository(session)
        exists = await repo.exists_by_email("alice@example.com")
        print("exists after rollback:", exists)


if __name__ == "__main__":
    asyncio.run(main())
