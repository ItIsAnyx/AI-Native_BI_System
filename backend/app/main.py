import os
import uvicorn
from fastapi import FastAPI
from app.config import settings
from app.database.db import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from openai import AsyncOpenAI, DefaultAsyncHttpxClient
from contextlib import asynccontextmanager
from starlette.concurrency import run_in_threadpool

from app.api.auth import router as auth_router
from app.api.user import router as user_router
from app.api.chat import router as chat_router
from app.api.workspace import router as workspace_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await run_in_threadpool(Base.metadata.create_all, bind=engine)
    print("БД инициализирована")
    async with AsyncOpenAI(
        base_url=settings.OLLAMA_BASE_URL,
        api_key="ollama",
        timeout=settings.REQUEST_TIMEOUT_SECONDS,
        max_retries=0,
        # Local inference must bypass system proxies, which can buffer streams
        # and keep generating after the application's connection has closed.
        http_client=DefaultAsyncHttpxClient(trust_env=False),
    ) as client:
        app.state.llm_client = client
        yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/auth")
app.include_router(user_router, prefix="/api/users")
app.include_router(chat_router)
app.include_router(workspace_router)

if __name__ == "__main__":
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
