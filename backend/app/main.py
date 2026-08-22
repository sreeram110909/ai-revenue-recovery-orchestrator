"""FastAPI Application Entry Point.

AI Revenue Recovery Orchestrator (Backend).
Wires configuration, database initialization, and health endpoint.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .database import create_db_engine, create_tables, get_session_factory
from .routers.cases import router as cases_router
from .routers.batch import router as batch_router
from .routers.webhooks import router as webhooks_router

logger = logging.getLogger(__name__)

# Global references set during lifespan
engine = None
SessionFactory = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    global engine, SessionFactory

    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    )

    logger.info("Starting AI Revenue Recovery Orchestrator (env=%s)", settings.environment)

    # Initialize database
    engine = create_db_engine()
    SessionFactory = get_session_factory(engine)
    create_tables(engine)

    if settings.is_sqlite_fallback:
        logger.warning("Running with SQLite fallback. Set DATABASE_URL for PostgreSQL.")
    else:
        logger.info("Connected to PostgreSQL database.")

    if not settings.has_razorpay_credentials:
        logger.info("Razorpay credentials not configured. Execution will use mocked responses in tests.")

    if not settings.has_gemini_credentials:
        logger.info("Gemini API key not configured. Diagnosis will use rule-based fallback.")

    yield

    # Shutdown
    if engine:
        engine.dispose()
        logger.info("Database engine disposed.")


app = FastAPI(
    title="AI Revenue Recovery Orchestrator",
    description="Autonomous policy-governed revenue recovery engine for failed payments and recurring subscription charges.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Modular API Routers
app.include_router(cases_router)
app.include_router(batch_router)
app.include_router(webhooks_router)


@app.get("/health")
async def health_check():
    """Service health endpoint. Reports database backend and credential status."""
    settings = get_settings()
    return {
        "status": "healthy",
        "service": "ai-revenue-recovery-orchestrator",
        "version": "1.0.0",
        "environment": settings.environment,
        "database": "postgresql" if not settings.is_sqlite_fallback else "sqlite (local dev fallback)",
        "razorpay_configured": settings.has_razorpay_credentials,
        "gemini_configured": settings.has_gemini_credentials,
    }
