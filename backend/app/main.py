import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1 import chat, documents
from app.config import settings
from app.db.database import init_db

# Ensure logs are visible in tests (no uvicorn handler) without double-adding
# a handler when uvicorn is present.
if not logging.root.handlers:
    logging.basicConfig(
        level=logging.INFO,
        format="%(levelname)s:%(name)s:%(message)s",
    )

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        # 1. SQLite — create dir + tables
        init_db()
        logger.info("SQLite initialised at %s", settings.sqlite_path)

        # 2. Chroma — 翻车点 2 规避: mkdir + 写权限检查
        settings.chroma_path.mkdir(parents=True, exist_ok=True)
        if not os.access(settings.chroma_path, os.W_OK):
            raise RuntimeError(f"Chroma path not writable: {settings.chroma_path}")
        logger.info("Chroma path ready: %s", settings.chroma_path)
        # Step 3: log ChromaStore(settings.chroma_path).count() here

        # 3. Uploads dir
        settings.uploads_path.mkdir(parents=True, exist_ok=True)
        logger.info("Uploads path ready: %s", settings.uploads_path)
    except Exception:
        logger.exception("Startup failed")
        raise

    logger.info("Application startup complete")
    yield
    logger.info("Application shutdown")


app = FastAPI(title="Document Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
