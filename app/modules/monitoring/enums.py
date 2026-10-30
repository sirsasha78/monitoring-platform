from enum import StrEnum


class CheckStatus(StrEnum):
    """Статус проверки сервиса."""

    UP = "up"
    DOWN = "down"
    UNKNOWN = "unknown"


class ErrorType(StrEnum):
    """Тип ошибки."""

    TIMEOUT = "timeout"
    CONNECTION_ERROR = "connection_error"
    HTTP_ERROR = "http_error"
    SSL_ERROR = "ssl_error"
    DNS_ERROR = "dns_error"
