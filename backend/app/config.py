from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_PATH,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )

    DB_USERNAME: str
    DB_PASSWORD: str
    DB_PORT: int = Field(ge=1, le=65535)
    DB_DATABASE: str
    DB_HOST: str

    COOKIE_SECURE: bool
    COOKIE_SAMESITE: Literal["lax", "strict", "none"]

    SECRET_KEY: str
    ALGORITHM: Literal["HS256"]
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(gt=0)
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(gt=0)

    FRONTEND_URL: str

    @field_validator("COOKIE_SAMESITE", mode="before")
    @classmethod
    def normalize_same_site(cls, value):
        return value.lower() if isinstance(value, str) else value

    @model_validator(mode="after")
    def validate_cookie_settings(self):
        if self.COOKIE_SAMESITE == "none" and not self.COOKIE_SECURE:
            raise ValueError("SameSite=None requires COOKIE_SECURE=true")
        return self

settings = Settings()
