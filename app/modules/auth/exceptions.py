class AuthError(Exception):
    """Базовое исключение модуля auth."""


class EmailAlreadyExistsError(AuthError):
    """Email уже зарегистрирован."""


class UsernameAlreadyExistsError(AuthError):
    """Username уже занят."""


class InvalidCredentialsError(AuthError):
    """Неверный email или пароль."""


class InactiveUserError(AuthError):
    """Пользователь заблокирован."""


class InvalidTokenError(AuthError):
    """Токен невалиден или истёк."""
