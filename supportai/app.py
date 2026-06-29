import logging
import os
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .exceptions import register_exception_handlers
from .middleware.auth import AuthMiddleware
from .middleware.logging import RequestLoggingMiddleware
from .middleware.ratelimit import RateLimitMiddleware
from .routes import router as api_router

logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper()),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting SupportAI backend v2...")

    db = None
    try:
        from .db.database import Database

        db = Database()
        await db.connect()
        logger.info("Database connected.")
    except Exception as e:
        logger.warning("Database not available: %s", e)
    app.state.db = db

    pipeline = None
    try:
        from .ml.pipeline import ChatPipeline
        from .services.session import SessionManager

        session_mgr = SessionManager()
        pipeline = ChatPipeline(db=db, session_manager=session_mgr)
        logger.info("Chat pipeline initialized.")
    except Exception as e:
        logger.warning("Chat pipeline not available: %s", e)
    app.state.pipeline = pipeline

    app.state.startup_time = time.time()
    logger.info("SupportAI backend started.")

    yield

    logger.info("Shutting down SupportAI backend...")
    if db is not None:
        try:
            await db.disconnect()
            logger.info("Database disconnected.")
        except Exception as e:
            logger.warning("Error disconnecting database: %s", e)


app = FastAPI(
    title="SupportAI API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

cors_origins = os.getenv("CORS_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-Id", "Retry-After"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware)

register_exception_handlers(app)

app.include_router(api_router)


@app.get("/")
async def root():
    return {
        "service": "SupportAI API",
        "version": "2.0.0",
        "status": "running",
        "docs": "/docs",
    }
