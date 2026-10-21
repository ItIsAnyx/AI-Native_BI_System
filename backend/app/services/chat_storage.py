import base64
import shutil
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException

from app.config import settings


def storage_path(relative_path: str) -> Path:
    root = settings.STORAGE_DIR.resolve()
    if not settings.STORAGE_DIR.is_absolute():
        root = (Path(__file__).resolve().parents[2] / settings.STORAGE_DIR).resolve()
    path = (root / relative_path).resolve()
    if not path.is_relative_to(root):
        raise ValueError("File path is outside storage")
    return path


def save_csv(file, chat_id: UUID, source_id: UUID) -> str:
    relative_path = f"sources/{chat_id}/{source_id}.csv"
    path = storage_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    file.seek(0)
    destination = path.open("xb")
    try:
        with destination:
            shutil.copyfileobj(file, destination, length=64 * 1024)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return relative_path


def save_png(encoded: str, chat_id: UUID, artifact_id: UUID) -> str:
    data = base64.b64decode(encoded, validate=True)
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("Chart did not contain a PNG image")
    relative_path = f"artifacts/{chat_id}/{artifact_id}.png"
    path = storage_path(relative_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    destination = path.open("xb")
    try:
        with destination:
            destination.write(data)
    except Exception:
        path.unlink(missing_ok=True)
        raise
    return relative_path


def remove_file(relative_path: str) -> None:
    storage_path(relative_path).unlink(missing_ok=True)


def existing_file(relative_path: str) -> Path:
    path = storage_path(relative_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Stored file not found")
    return path
