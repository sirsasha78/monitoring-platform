from datetime import timedelta

import jwt
import pytest

from app.core.security import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_password_produces_different_hashes() -> None:
    """Тест на два вызова hash_password("same") → разные строки (соль)."""

    hash_1 = hash_password("same")
    hash_2 = hash_password("same")
    assert hash_1 != hash_2


def test_verify_password_correct() -> None:
    """Тест на хеширивание корректного пароля."""

    password_hash = hash_password("secret")
    assert verify_password("secret", password_hash) is True


def test_verify_password_incorrect() -> None:
    """Тест на хеширивание некорректного пароля."""

    password_hash = hash_password("secret")
    assert verify_password("secret123", password_hash) is False


def test_create_and_decode_token() -> None:
    """Тест на создание и декодирование access_token."""

    access_token = create_access_token("4")
    payload = decode_access_token(access_token)
    assert payload["sub"] == "4"


def test_create_token_sub_is_string() -> None:
    """Тест на создание и проверку типа sub."""

    access_token = create_access_token(42)
    payload = decode_access_token(access_token)
    assert isinstance(payload["sub"], str)


def test_decode_expired_token() -> None:
    """Тест на истекший access_token."""

    access_token = create_access_token("4", timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_access_token(access_token)


def test_decode_garbage_token() -> None:
    """Тест на мусорный access_token."""

    with pytest.raises(jwt.InvalidTokenError):
        decode_access_token("garbage.token")
