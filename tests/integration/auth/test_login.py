from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token, hash_password
from app.modules.auth.models import User


async def test_login_success(client: AsyncClient, registered_user: dict[str, str]) -> None:
    """Тест на успешную авторизацию."""

    response = await client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": registered_user["password"]},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["token_type"] == "bearer"

    payload = decode_access_token(data["access_token"])
    assert payload["sub"] == str(registered_user["id"])


async def test_login_wrong_password(client: AsyncClient, registered_user: dict[str, str]) -> None:
    """Проверяет авторизацию с неверным паролем."""

    response = await client.post(
        "/auth/login",
        data={"username": registered_user["email"], "password": "wrong_password"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль."


async def test_login_nonexistent_email(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """Проверяет авторизацию с несуществующим email."""

    response = await client.post(
        "/auth/login",
        data={"username": "nobody@example.com", "password": registered_user["password"]},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Неверный email или пароль."


async def test_login_inactive_user(client: AsyncClient, db_session: AsyncSession) -> None:
    """Проверяет авторизацию не активного пользователя."""

    user = User(
        username="inactive",
        email="inactive@example.com",
        password_hash=hash_password("secret123"),
        is_active=False,
    )
    db_session.add(user)
    await db_session.commit()

    response = await client.post(
        "/auth/login", data={"username": "inactive@example.com", "password": "secret123"}
    )
    assert response.status_code == 403
