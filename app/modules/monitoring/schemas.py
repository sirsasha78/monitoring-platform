from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.modules.monitoring.enums import CheckStatus


class ServiceCreate(BaseModel):
    """Модель для создания сервиса."""

    name: Annotated[str, Field(min_length=1, max_length=100)]
    url: Annotated[
        HttpUrl,
        Field(description="Адрес сервиса, который проверяем.", examples=["http://example.com"]),
    ]
    method: Annotated[Literal["GET", "POST", "HEAD"], Field(description="HTTP-метод")] = "GET"
    interval_seconds: Annotated[
        int, Field(ge=10, le=3600, description="Как часто проверять сервис.")
    ] = 60
    timeout_seconds: Annotated[int, Field(ge=1, le=60)] = 10
    expected_status_codes: Annotated[str, Field(max_length=50)] = "2xx"
    failure_threshold: Annotated[int, Field(ge=1, le=10)] = 3
    recovery_threshold: Annotated[int, Field(ge=1, le=10)] = 2


class ServiceUpdate(BaseModel):
    """Модель для обновления данных сервиса."""

    name: Annotated[str, Field(min_length=1, max_length=100)] | None = None
    url: (
        Annotated[
            HttpUrl,
            Field(
                description="Адрес сервиса, который проверяем.", examples=["http://example.com"]
            ),
        ]
        | None
    ) = None
    method: Annotated[Literal["GET", "POST", "HEAD"], Field(description="HTTP-метод")] | None = (
        None
    )
    interval_seconds: (
        Annotated[int, Field(ge=10, le=3600, description="Как часто проверять сервис.")] | None
    ) = None
    timeout_seconds: Annotated[int, Field(ge=1, le=60)] | None = None
    expected_status_codes: Annotated[str, Field(max_length=50)] | None = None
    failure_threshold: Annotated[int, Field(ge=1, le=10)] | None = None
    recovery_threshold: Annotated[int, Field(ge=1, le=10)] | None = None
    is_active: bool | None = None


class ServiceRead(BaseModel):
    """Модель для чтения данных сервиса."""

    id: int
    user_id: int
    name: str
    url: str
    method: str
    interval_seconds: int
    timeout_seconds: int
    expected_status_codes: str
    failure_threshold: int
    recovery_threshold: int
    current_status: CheckStatus
    last_check_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
