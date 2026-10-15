from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Хеширует пароль с помощью bcrypt."""

    password_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt()
    hashed_bytes = bcrypt.hashpw(password_bytes, salt)

    return hashed_bytes.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Проверяет, соответствует ли пароль сохранённому хешу."""

    password_bytes = password.encode("utf-8")
    password_hash_bytes = password_hash.encode("utf-8")

    return bcrypt.checkpw(password_bytes, password_hash_bytes)


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Создаёт JWT access-токен."""

    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)

    now = datetime.now(UTC)

    payload: dict[str, Any] = {
        "sub": str(subject),
        "exp": now + expires_delta,
        "iat": now,
    }

    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Декодирует JWT access-токен."""

    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
