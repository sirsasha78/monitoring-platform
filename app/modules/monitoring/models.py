from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.monitoring.enums import CheckStatus

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

    def __repr__(self) -> str:
        return f"<Service(id={self.id}, name={self.name})>"
