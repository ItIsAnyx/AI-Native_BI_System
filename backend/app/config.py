from pathlib import Path
from typing import Literal
from secrets import compare_digest
from fastapi import HTTPException
from pydantic import Field
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

    FRONTEND_URL: str = "http://localhost:5174"
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434/v1"

    MODEL_NAME: str = ""
    REQUEST_TIMEOUT_SECONDS: float = Field(default=300, gt=0)
    MAX_REQUEST_LENGTH: int = Field(default=8000, gt=0)
    MAX_CONTEXT_LENGTH: int = Field(default=24000, gt=0)
    TOKENIZER_PATH: Path = ENV_PATH.parent / "models" / "tokenizer"
    MAX_CONTEXT_TOKENS: int = Field(default=40960, gt=0)
    MAX_RESPONSE_TOKENS: int = Field(default=4096, gt=0)
    MAX_CONTINUATIONS: int = Field(default=2, ge=1)
    MAX_FILE_SIZE_MB: int = Field(default=10, gt=0)
    MAX_FILE_ROWS: int = Field(default=100000, gt=0)
    MAX_TOOL_CALLS: int = Field(default=5, gt=0)
    STORAGE_DIR: Path = ENV_PATH.parent / "storage"
    # Named analytical PostgreSQL connections. Credentials never go to the model or browser.
    ANALYTICS_CONNECTIONS: dict[str, str] = Field(default_factory=dict)
    ANALYTICS_TIMEOUT_MS: int = Field(default=30000, ge=1000, le=300000)
    QUERY_TIMEOUT_SECONDS: float = Field(default=30, gt=0, le=300)
    QUERY_MEMORY_MB: int = Field(default=512, ge=64, le=4096)
    QUERY_MAX_ROWS: int = Field(default=100000, ge=1, le=1000000)

settings = Settings()
