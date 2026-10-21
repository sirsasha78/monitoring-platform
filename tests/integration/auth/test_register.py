from httpx import AsyncClient


async def test_register_success(client: AsyncClient, user_data: dict[str, str]) -> None:
    """Успешная регистрация возвращает 201 и данные без пароля."""

    response = await client.post("/auth/register", json=user_data)
    assert response.status_code == 201
    data = response.json()

    assert data["username"] == user_data["username"]
    assert data["email"] == user_data["email"]

    assert "id" in data
    assert "created_at" in data
    assert "is_active" in data
    assert "notify_via_email" in data
    assert "notify_via_telegram" in data

    assert "password" not in data
    assert "password_hash" not in data


async def test_register_duplicate_email(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """Регистрация с существующим email."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "different_username",
            "email": registered_user["email"],
            "password": "secret123",
        },
    )
    assert response.status_code == 409


async def test_register_duplicate_username(
    client: AsyncClient, registered_user: dict[str, str]
) -> None:
    """Регистрация с существующим username."""

    response = await client.post(
        "/auth/register",
        json={
            "username": registered_user["username"],
            "email": "bob@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 409


async def test_register_invalid_email(client: AsyncClient) -> None:
    """Регистрация с существующим с некорректным email."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "bob",
            "email": "bobexample.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 422


async def test_register_password_without_digit(client: AsyncClient) -> None:
    """Пароль без цифры (но валидной длины) отклоняется."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "alice_92",
            "email": "alice@example.com",
            "password": "onlyletters",
        },
    )
    assert response.status_code == 422


async def test_register_password_without_letter(client: AsyncClient) -> None:
    """Пароль без буквы (но валидной длины) отклоняется."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "bob_42",
            "email": "bob@example.com",
            "password": "12345678",
        },
    )
    assert response.status_code == 422


async def test_register_short_password(client: AsyncClient) -> None:
    """Слишком короткий пароль отклоняется (min_length)."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "carol_1",
            "email": "carol@example.com",
            "password": "a1",
        },
    )
    assert response.status_code == 422


async def test_register_uppercase_username(client: AsyncClient) -> None:
    """Регистрация с некорректным username."""
    response = await client.post(
        "/auth/register",
        json={
            "username": "ALICE",
            "email": "alice@example.com",
            "password": "secret123",
        },
    )
    assert response.status_code == 422


async def test_register_email_normalized(client: AsyncClient) -> None:
    """При регистраци email переводится в нижний регистр."""

    response = await client.post(
        "/auth/register",
        json={
            "username": "alice_92",
            "email": "Alice@Example.COM",
            "password": "secret123",
        },
    )
    assert response.status_code == 201
    data = response.json()

    assert data["email"] == "alice@example.com"
