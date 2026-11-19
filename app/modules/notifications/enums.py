from enum import StrEnum


class NotificationChannel(StrEnum):
    """Канал по которому будут приходить уведомления."""

    EMAIL = "email"


class NotificationStatus(StrEnum):
    """Статус уведомления."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"
