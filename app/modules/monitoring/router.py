from fastapi import APIRouter, status

from app.modules.auth.dependencies import CurrentUserDep
from app.modules.monitoring.schemas import ServiceCreate, ServiceRead, ServiceUpdate
from app.modules.monitoring.service import MonitoringServiceDep

router = APIRouter(prefix="/services", tags=["services"])


@router.post("", response_model=ServiceRead, status_code=status.HTTP_201_CREATED)
async def create_service(
    data: ServiceCreate, service_dep: MonitoringServiceDep, current_user: CurrentUserDep
) -> ServiceRead:
    """Эндпоинт для создания нового сервиса."""

    service = await service_dep.create(current_user.id, data)

    return ServiceRead.model_validate(service)


@router.get("", response_model=list[ServiceRead])
async def get_services_for_user(
    service_dep: MonitoringServiceDep, current_user: CurrentUserDep
) -> list[ServiceRead]:
    """Эндпоинт для получения всех сервисов текущего пользователя."""

    services = await service_dep.list_for_user(current_user.id)

    return [ServiceRead.model_validate(s) for s in services]


@router.get("/{service_id}", response_model=ServiceRead)
async def get_service_by_id(
    service_id: int, service_dep: MonitoringServiceDep, current_user: CurrentUserDep
) -> ServiceRead:
    """Эндпоинт для получения сервиса по ID."""

    service = await service_dep.get_for_user(current_user.id, service_id)

    return ServiceRead.model_validate(service)


@router.patch("/{service_id}", response_model=ServiceRead)
async def update_service(
    service_id: int,
    data: ServiceUpdate,
    service_dep: MonitoringServiceDep,
    current_user: CurrentUserDep,
) -> ServiceRead:
    """Эндпоинт для обновления сервиса."""

    service = await service_dep.update(current_user.id, service_id, data)

    return ServiceRead.model_validate(service)


@router.delete("/{service_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_service(
    service_id: int, service_dep: MonitoringServiceDep, current_user: CurrentUserDep
) -> None:
    """Эндпоинт для удаления сервиса."""

    await service_dep.delete(current_user.id, service_id)
