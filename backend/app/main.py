from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from app.config import settings
from app.agent.agent import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.generator = None
    if settings.MODEL_PATH:
        from transformers import pipeline

        model_path = Path(settings.MODEL_PATH)
        if not model_path.is_absolute():
            model_path = Path(__file__).resolve().parents[1] / model_path
        if not model_path.is_dir():
            raise ValueError(f"Model directory does not exist: {model_path}")

        app.state.generator = pipeline(
            task="text-generation",
            model=str(model_path),
            tokenizer=str(model_path),
            model_kwargs={"local_files_only": True},
            dtype="auto",
            device_map="auto",
        )
    try:
        yield
    finally:
        app.state.generator = None


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.include_router(agent_router)
