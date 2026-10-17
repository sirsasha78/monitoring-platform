from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserRegister(BaseModel):
    """Модель для регистрации пользователя."""

    username: Annotated[
        str,
        Field(
            min_length=3,
            max_length=50,
            pattern=r"^[a-z0-9_]{3,50}$",
            description="Логин: строчные латинские буквы, цифры и подчёркивание.",
            examples=["alice_92"],
        ),
    ]
    email: EmailStr
    password: Annotated[
        str,
        Field(
            min_length=8,
            max_length=100,
            description="Пароль: минимум 8 символов, должен содержать буквы и цифры.",
        ),
    ]

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        return value.lower()

    @field_validator("password")
    @classmethod
    def check_password(cls, value: str) -> str:
        if not any(letter.isalpha() for letter in value) or not any(
            letter.isdigit() for letter in value
        ):
            raise ValueError("Пароль должен содержать хотя бы одну букву и цифру")

        return value


class UserRead(BaseModel):
    """Модель для ответа с данными пользователя."""

    id: int
    username: str
    email: str
    is_active: bool
    notify_via_email: bool
    notify_via_telegram: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Модель для данных токена."""

    access_token: str
    token_type: str = "bearer"
