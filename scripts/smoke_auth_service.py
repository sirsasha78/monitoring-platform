"""Smoke-тест для AuthService."""

import asyncio

from app.core.database import SessionLocal
from app.modules.auth.exceptions import (
    EmailAlreadyExistsError,
    InvalidCredentialsError,
    UsernameAlreadyExistsError,
)
from app.modules.auth.schemas import UserRegister
from app.modules.auth.service import AuthService


async def main() -> None:
    async with SessionLocal() as session:
        service = AuthService(session)

        # 1. Успешная регистрация
        data = UserRegister(
            username="bob_42",
            email="bob@example.com",
            password="secret123",
        )
        user = await service.register(data)
        print("registered:", user)
        print("user id:", user.id)
        print("created_at:", user.created_at)

        # 2. Повторный email
        try:
            await service.register(
                UserRegister(
                    username="bob_43",
                    email="bob@example.com",
                    password="secret123",
                )
            )
        except EmailAlreadyExistsError as e:
            print("email exists:", e)

        # 3. Повторный username
        try:
            await service.register(
                UserRegister(
                    username="bob_42",
                    email="other@example.com",
                    password="secret123",
                )
            )
        except UsernameAlreadyExistsError as e:
            print("username exists:", e)

        # 4. Успешный логин
        token = await service.login("bob@example.com", "secret123")
        print("token:", token[:20], "...")

        # 5. Неверный пароль
        try:
            await service.login("bob@example.com", "wrong")
        except InvalidCredentialsError as e:
            print("wrong password:", e)

        # 6. Несуществующий email
        try:
            await service.login("nobody@example.com", "secret123")
        except InvalidCredentialsError as e:
            print("no user:", e)

        # Откат, чтобы не засорять БД
        await session.rollback()
        print("rolled back")


if __name__ == "__main__":
    asyncio.run(main())
