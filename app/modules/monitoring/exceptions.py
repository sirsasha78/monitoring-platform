class MonitoringError(Exception):
    """Базовое исключение модуля monitoring."""

    pass


class ServiceNotFoundError(MonitoringError):
    """Сервис не найден."""

    pass
