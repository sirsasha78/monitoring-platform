from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.incidents.enums import IncidentStatus
from app.modules.monitoring.enums import ErrorType


class IncidentRead(BaseModel):
    """Модель для отдачи инцидента клиенту."""

    id: int
    service_id: int
    started_at: datetime
    resolved_at: datetime | None
    status: IncidentStatus
    trigger_error_type: ErrorType | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
