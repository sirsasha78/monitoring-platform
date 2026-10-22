from enum import StrEnum


class CheckStatus(StrEnum):
    """Статус проверки сервиса."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"
