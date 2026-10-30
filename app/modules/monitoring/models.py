from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.monitoring.enums import CheckStatus, ErrorType

if TYPE_CHECKING:
    from app.modules.auth.models import User


class Service(Base):
    """Сервис, который пользователь мониторит."""

    __tablename__ = "services"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(2048))
    method: Mapped[str] = mapped_column(String(10), server_default="GET")
    interval_seconds: Mapped[int] = mapped_column(server_default=text("60"))
    timeout_seconds: Mapped[int] = mapped_column(server_default=text("10"))
    expected_status_codes: Mapped[str] = mapped_column(String(50), server_default="2xx")
    failure_threshold: Mapped[int] = mapped_column(server_default=text("3"))
    recovery_threshold: Mapped[int] = mapped_column(server_default=text("2"))
    current_status: Mapped[CheckStatus] = mapped_column(
        SAEnum(
            CheckStatus,
            name="check_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        server_default=CheckStatus.UNKNOWN.value,
    )
    last_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user: Mapped["User"] = relationship("User", back_populates="services")
    check_results: Mapped[list["CheckResult"]] = relationship(
        "CheckResult", back_populates="service", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name})>"


class CheckResult(Base):
    """Модель для результата проверки."""

    __tablename__ = "check_results"
    __table_args__ = (
        Index("ix_check_results_service_id_checked_at", "service_id", "checked_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    service_id: Mapped[int] = mapped_column(ForeignKey("services.id", ondelete="CASCADE"))
    checked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    status: Mapped[CheckStatus] = mapped_column(
        SAEnum(
            CheckStatus,
            name="check_status",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        )
    )
    status_code: Mapped[int | None] = mapped_column(nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(nullable=True)
    error_type: Mapped[ErrorType | None] = mapped_column(
        SAEnum(
            ErrorType,
            name="error_type",
            values_callable=lambda enum_cls: [member.value for member in enum_cls],
        ),
        nullable=True,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    service: Mapped["Service"] = relationship("Service", back_populates="check_results")

    def __repr__(self) -> str:
        return f"<CheckResult(id={self.id}, service_id={self.service_id}, status={self.status})>"
