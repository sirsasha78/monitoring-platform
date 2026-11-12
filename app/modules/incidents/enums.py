from enum import StrEnum


class IncidentStatus(StrEnum):
    """Статус инцидента."""

    OPEN = "open"
    RESOLVED = "resolved"
