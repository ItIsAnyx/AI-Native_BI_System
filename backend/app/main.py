from contextlib import asynccontextmanager

from fastapi import FastAPI
from openai import AsyncOpenAI
from app.config import settings
from app.agent.agent import router as agent_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with AsyncOpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=settings.REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
    ) as client:
        app.state.llm_client = client
        yield


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)
app.include_router(agent_router)
