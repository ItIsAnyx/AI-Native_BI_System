import os
import uvicorn
from fastapi import FastAPI
from app.config import settings
from app.database.db import engine, Base
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from openai import AsyncOpenAI
from contextlib import asynccontextmanager

from app.api.auth import router as auth_router
from app.api.user import router as user_router
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
app.include_router(agent_router)

@app.on_event("startup")
async def Start():
    Base.metadata.create_all(bind=engine)
    print("БД инициализирована")

if __name__ == "__main__":
    os.environ["NO_PROXY"] = "localhost,127.0.0.1"
    uvicorn.run("app.main:app", host="0.0.0.0", port=8080, reload=True)
