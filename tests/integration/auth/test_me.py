from datetime import timedelta

from httpx import AsyncClient

from app.core.security import create_access_token


async def test_me_success(client: AsyncClient, registered_user: dict[str, str]) -> None:
    """Тест на успешный возврат текущего пользователя."""

    access_token = create_access_token(registered_user["id"])

    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == registered_user["id"]
    assert data["username"] == registered_user["username"]
    assert data["email"] == registered_user["email"]

    assert "password" not in data
    assert "password_hash" not in data


async def test_me_without_token(client: AsyncClient) -> None:
    """Проверяет возврат данных без токена."""

    response = await client.get("/auth/me")
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_with_garbage_token(client: AsyncClient) -> None:
    """Проверяет возврат данных с неправильным токеном."""

    response = await client.get("/auth/me", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


async def test_me_with_expired_token(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """Проверяет возврат данных с истекшим токеном."""

    access_token = create_access_token(registered_user["id"], expires_delta=timedelta(seconds=-1))

    response = await client.get("/auth/me", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == 401
