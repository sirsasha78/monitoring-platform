class IncidentsError(Exception):
    """Базовое исключение модуля incident."""

    pass


class IncidentNotFoundError(IncidentsError):
    """Инцидент не найден."""

    pass
