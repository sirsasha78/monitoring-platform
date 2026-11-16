from fastapi import APIRouter

from app.core.pagination import PaginationDep
from app.modules.auth.dependencies import CurrentUserDep
from app.modules.incidents.enums import IncidentStatus
from app.modules.incidents.models import Incident
from app.modules.incidents.schemas import IncidentRead
from app.modules.incidents.service import IncidentServiceDep

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.get("", response_model=list[IncidentRead])
async def list_incidents(
    current_user: CurrentUserDep,
    service: IncidentServiceDep,
    pagination: PaginationDep,
    status: IncidentStatus | None = None,
) -> list[Incident]:
    """Все инциденты текущего пользователя (новые сверху). Фильтр по status опционален."""

    return await service.list_by_user_id(
        current_user.id, pagination.limit, pagination.offset, status
    )


@router.get("/{incident_id}", response_model=IncidentRead)
async def get_incident(
    incident_id: int, current_user: CurrentUserDep, service: IncidentServiceDep
) -> Incident:
    """Один инцидент по id. Только свой, иначе 404."""

    return await service.get_for_user(current_user.id, incident_id)
