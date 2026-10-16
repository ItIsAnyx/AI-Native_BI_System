from pathlib import Path
from secrets import compare_digest

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from fastapi import HTTPException

class Settings(BaseSettings):
    APP_NAME: str = "AI-Native_BI_System"
    BACKEND_KEY: str = Field(min_length=1)
    OLLAMA_BASE_URL: str = "http://127.0.0.1:11434/v1"
    MODEL_NAME: str = ""
    REQUEST_TIMEOUT_SECONDS: float = Field(default=300, gt=0)
    MAX_REQUEST_LENGTH: int = Field(default=8000, gt=0)
    MAX_CONTEXT_LENGTH: int = Field(default=24000, gt=0)
    MAX_FILE_SIZE_MB: int = Field(default=10, gt=0)
    MAX_FILE_ROWS: int = Field(default=100000, gt=0)

    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[1] / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

settings = Settings()

def validate_key(backend_key: str):
    if not compare_digest(backend_key.encode(), settings.BACKEND_KEY.encode()):
        raise HTTPException(status_code=403, detail="Forbidden: BACKEND_KEY is invalid")
