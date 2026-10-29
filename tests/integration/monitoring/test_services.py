from httpx import AsyncClient


async def test_create_service_success(
    client: AsyncClient,
    registered_user: dict[str, str],
    auth_headers: dict[str, str],
    service_data: dict[str, object],
) -> None:
    """Проверяет успешное создание сервиса."""

    response = await client.post("/services", json=service_data, headers=auth_headers)

    assert response.status_code == 201
    data = response.json()

    assert data["name"] == service_data["name"]
    assert data["url"] == service_data["url"]
    assert data["interval_seconds"] == service_data["interval_seconds"]
    assert data["user_id"] == registered_user["id"]


async def test_create_service_unauthorized(
    client: AsyncClient, service_data: dict[str, object]
) -> None:
    """Проверяет создание сервиса не авторизированным пользователем."""

    response = await client.post("/services", json=service_data)
    assert response.status_code == 401


async def test_create_service_invalid_url(
    client: AsyncClient, service_data: dict[str, object], auth_headers: dict[str, str]
) -> None:
    """Проверяет создание сервиса с невалидным url."""

    data = {**service_data, "url": "not-a-url"}
    response = await client.post("/services", json=data, headers=auth_headers)
    assert response.status_code == 422


async def test_create_service_interval_too_small(
    client: AsyncClient, service_data: dict[str, object], auth_headers: dict[str, str]
) -> None:
    """Проверяет создание сервиса с невалидным interval_seconds."""

    data = {**service_data, "interval_seconds": 5}
    response = await client.post("/services", json=data, headers=auth_headers)
    assert response.status_code == 422


async def test_list_services_empty(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Проверяет получение списка сервисов."""

    response = await client.get("/services", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data == []


async def test_list_services_only_mine(
    client: AsyncClient,
    service_data: dict[str, object],
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    """Пользователь видит только свои сервисы."""

    for name in ("Service A", "Service B"):
        response = await client.post(
            "/services", json={**service_data, "name": name}, headers=auth_headers
        )
        assert response.status_code == 201

    response = await client.post("/services", json=service_data, headers=second_user_headers)
    assert response.status_code == 201

    lst_first_user = (await client.get("/services", headers=auth_headers)).json()
    assert len(lst_first_user) == 2

    lst_second_user = (await client.get("/services", headers=second_user_headers)).json()
    assert len(lst_second_user) == 1


async def test_get_service_by_id_success(
    client: AsyncClient, service_data: dict[str, object], auth_headers: dict[str, str]
) -> None:
    """Проверяет получение сервиса по ID."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    response = await client.get(f"/services/{service_id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == service_data["name"]
    assert data["url"] == service_data["url"]
    assert data["interval_seconds"] == service_data["interval_seconds"]


async def test_get_service_not_found(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Проверяет попытку получить несуществующий сервис."""

    response = await client.get("/services/999999", headers=auth_headers)
    assert response.status_code == 404


async def test_get_foreign_service_returns_404(
    client: AsyncClient,
    service_data: dict[str, object],
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    """Чужой сервис → 404 (не 403 — не раскрываем существование)."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    response = await client.get(f"/services/{service_id}", headers=second_user_headers)
    assert response.status_code == 404


async def test_update_service_partial(
    client: AsyncClient, service_data: dict[str, object], auth_headers: dict[str, str]
) -> None:
    """PATCH обновляет только переданные поля, остальные не трогает."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    original = response.json()
    service_id = response.json()["id"]

    response = await client.patch(
        f"/services/{service_id}", json={"name": "new"}, headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()

    assert data["name"] == "new"
    assert data["url"] == original["url"]
    assert data["interval_seconds"] == original["interval_seconds"]
    assert data["method"] == original["method"]


async def test_update_foreign_service_returns_404(
    client: AsyncClient,
    service_data: dict[str, object],
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    """PATCH чужого сервиса → 404."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    response = await client.patch(
        f"/services/{service_id}", json={"name": "new"}, headers=second_user_headers
    )
    assert response.status_code == 404


async def test_delete_service_success(
    client: AsyncClient, service_data: dict[str, object], auth_headers: dict[str, str]
) -> None:
    """DELETE удаляет сервис."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    response = await client.delete(f"/services/{service_id}", headers=auth_headers)
    assert response.status_code == 204

    response = await client.get(f"/services/{service_id}", headers=auth_headers)
    assert response.status_code == 404


async def test_delete_foreign_service_returns_404(
    client: AsyncClient,
    service_data: dict[str, object],
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
) -> None:
    """Проверяет попытку удалить чужой сервис."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    response = await client.delete(f"/services/{service_id}", headers=second_user_headers)
    assert response.status_code == 404


async def test_delete_service_unauthorized(
    client: AsyncClient, service_data: dict[str, object], auth_headers: dict[str, str]
) -> None:
    """DELETE без токена → 401."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    response = await client.delete(f"/services/{service_id}")
    assert response.status_code == 401
