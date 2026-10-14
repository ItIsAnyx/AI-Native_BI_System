from fastapi import UploadFile, HTTPException

from app.config import settings

async def check_loading_file(file: UploadFile) -> None:
    if not (file.filename or "").lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files allowed")
    limit = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    # Читаем частями, не загружая весь файл в память.
    total = 0
    try:
        while chunk := await file.read(64 * 1024):
            total += len(chunk)
            if total > limit:
                raise HTTPException(status_code=413, detail="File too large")
    finally:
        await file.seek(0)
