from typing import Annotated

from pydantic import BaseModel, Field, StringConstraints, ValidationInfo, field_validator
from pydantic_core import PydanticCustomError


Email = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=255,
        pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$",
    ),
]
Login = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=3, max_length=255),
]


class LoginUserRequest(BaseModel):
    email: Email
    password: str = Field(min_length=1)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        if not value.strip():
            raise PydanticCustomError("password_empty", "Введите пароль")
        return value


class RegisterUserRequest(LoginUserRequest):
    login: Login
    password: str = Field(min_length=8)
    repeat_password: str = Field(min_length=1)

    @field_validator("repeat_password")
    @classmethod
    def validate_repeat_password(cls, value: str, info: ValidationInfo) -> str:
        password = info.data.get("password")
        if password is not None and value != password:
            raise PydanticCustomError("password_mismatch", "Пароли не совпадают")
        return value
