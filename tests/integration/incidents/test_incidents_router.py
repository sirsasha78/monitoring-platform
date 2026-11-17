from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident
from app.modules.monitoring.enums import ErrorType


async def _create_incident(
    db_session: AsyncSession,
    service_id: int,
    status: IncidentStatus = IncidentStatus.OPEN,
    started_at: datetime | None = None,
) -> Incident:
    """Хелпер для создания инцидента."""

    incident = Incident(
        service_id=service_id,
        started_at=started_at or datetime.now(UTC),
        status=status,
        trigger_error_type=ErrorType.TIMEOUT,
    )
    db_session.add(incident)
    await db_session.commit()
    await db_session.refresh(incident)
    return incident


async def test_list_incidents_empty(client: AsyncClient, auth_headers: dict[str, str]) -> None:
    """Нет инцидентов → GET /incidents → 200, пустой список."""

    response = await client.get("/incidents", headers=auth_headers)

    assert response.status_code == 200
    assert response.json() == []


async def test_list_incidents_only_mine(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """User A: 2 инцидента, User B: 1 → каждый видит только свои."""

    service1 = await client.post(
        "/services", json={**service_data, "name": "Service1"}, headers=auth_headers
    )
    assert service1.status_code == 201
    service_1_id = service1.json()["id"]

    service2 = await client.post(
        "/services", json={**service_data, "name": "Service2"}, headers=auth_headers
    )
    assert service2.status_code == 201
    service_2_id = service2.json()["id"]

    service3 = await client.post(
        "/services", json={**service_data, "name": "Service3"}, headers=second_user_headers
    )
    assert service3.status_code == 201
    service_3_id = service3.json()["id"]

    inc_s1 = await _create_incident(db_session, service_1_id)
    inc_s2 = await _create_incident(db_session, service_2_id)
    inc_s3 = await _create_incident(db_session, service_3_id)

    response_a = await client.get("/incidents", headers=auth_headers)
    assert response_a.status_code == 200
    assert len(response_a.json()) == 2
    assert {inc["id"] for inc in response_a.json()} == {inc_s1.id, inc_s2.id}

    response_b = await client.get("/incidents", headers=second_user_headers)
    assert response_b.status_code == 200
    assert len(response_b.json()) == 1
    assert response_b.json()[0]["id"] == inc_s3.id


async def test_list_incidents_filter_status(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """
    3 инцидента (2 open, 1 resolved) → без фильтра 3, ?status=open → 2, ?status=resolved → 1.
    """

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    incident1 = await _create_incident(db_session, service_id)
    incident2 = await _create_incident(db_session, service_id)
    incident3 = await _create_incident(db_session, service_id, status=IncidentStatus.RESOLVED)

    response = await client.get("/incidents", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 3
    assert {inc["id"] for inc in response.json()} == {incident1.id, incident2.id, incident3.id}

    response = await client.get("/incidents?status=open", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2
    assert {inc["id"] for inc in response.json()} == {incident1.id, incident2.id}

    response = await client.get("/incidents?status=resolved", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert {inc["id"] for inc in response.json()} == {incident3.id}


async def test_list_incidents_limit(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """5 инцидентов, ?limit=2 → 2 записи (пагинация применяется)."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    for i in range(5):
        await _create_incident(
            db_session, service_id, started_at=datetime.now(UTC) - timedelta(minutes=i)
        )

    response = await client.get("/incidents?limit=2", headers=auth_headers)
    assert response.status_code == 200
    assert len(response.json()) == 2


async def test_list_incidents_order(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """Порядок: started_at DESC, при равенстве — id DESC."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    inc_old = await _create_incident(
        db_session, service_id, started_at=datetime.now(UTC) - timedelta(minutes=10)
    )
    inc_new = await _create_incident(
        db_session, service_id, started_at=datetime.now(UTC) - timedelta(minutes=1)
    )
    same_time = datetime.now(UTC) - timedelta(minutes=5)
    inc_same_1 = await _create_incident(db_session, service_id, started_at=same_time)
    inc_same_2 = await _create_incident(db_session, service_id, started_at=same_time)

    response = await client.get("/incidents", headers=auth_headers)
    assert response.status_code == 200

    assert len(response.json()) == 4
    assert response.json()[0]["id"] == inc_new.id
    assert [inc["id"] for inc in response.json()] == [
        inc_new.id,
        inc_same_2.id,
        inc_same_1.id,
        inc_old.id,
    ]


async def test_get_incident_success(
    client: AsyncClient,
    auth_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """GET /incidents/{id} своего инцидента → 200 с корректными полями."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    inc = await _create_incident(db_session, service_id)

    response = await client.get(f"/incidents/{inc.id}", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()

    assert data["id"] == inc.id
    assert data["service_id"] == service_id
    assert data["status"] == IncidentStatus.OPEN
    assert data["trigger_error_type"] == ErrorType.TIMEOUT
    assert data["started_at"] is not None
    assert data["resolved_at"] is None


async def test_get_foreign_incident_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """GET /incidents/{id} чужого инцидента → 404 (не 403, не 200)."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    inc = await _create_incident(db_session, service_id)

    response = await client.get(f"/incidents/{inc.id}", headers=second_user_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Инцидент не найден."


async def test_get_service_incidents_foreign_returns_404(
    client: AsyncClient,
    auth_headers: dict[str, str],
    second_user_headers: dict[str, str],
    service_data: dict[str, object],
    db_session: AsyncSession,
) -> None:
    """GET /services/{id}/incidents чужого сервиса → 404 (guard monitoring.get_for_user)."""

    response = await client.post("/services", json=service_data, headers=auth_headers)
    assert response.status_code == 201
    service_id = response.json()["id"]

    await _create_incident(db_session, service_id)
    await _create_incident(db_session, service_id)

    response = await client.get(f"/services/{service_id}/incidents", headers=second_user_headers)
    assert response.status_code == 404
    assert response.json()["detail"] == "Сервис не найден."
