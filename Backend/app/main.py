from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import create_tables, sync_schema
from app.api.v1.router import api_router
from app.services import evaluation_service
from app.services import stt_service

import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await sync_schema()
    evaluation_service.preload()  # warm up Sarah's BERT model (no-op if checkpoint missing)
    stt_service.preload()  # warm up Whisper (logs a warning instead of crashing if unavailable)
    yield

app = FastAPI(
    title=settings.APP_NAME,
    description="AI-powered recruitment platform API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Routes
app.include_router(api_router)

@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "ok", "app": settings.APP_NAME}