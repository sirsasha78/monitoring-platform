from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.incidents.enums import IncidentStatus
from app.modules.monitoring.enums import ErrorType

if TYPE_CHECKING:
    from app.modules.monitoring.models import Service


class Incident(Base):
    """Модель для инцидента."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_service_started", "service_id", "started_at"),
        Index("ix_incidents_open", "service_id", postgresql_where=text("status = 'open'")),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        SAEnum(
            IncidentStatus,
            name="incident_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default=IncidentStatus.OPEN.value,
    )
    trigger_error_type: Mapped[ErrorType | None] = mapped_column(
        SAEnum(
            ErrorType,
            name="error_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    last_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    message_count: Mapped[int] = mapped_column(server_default=text("0"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    service: Mapped["Service"] = relationship("Service", back_populates="incidents")

    def __repr__(self) -> str:
        return f"<Incident(id={self.id}, service_id={self.service_id}, status={self.status})>"
