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

    # Automatically and idempotently seed canonical demo & benchmark cases on fresh deployment
    try:
        session = SessionFactory()
        try:
            from .services.seed_service import seed_initial_cases_if_needed
            seeded_count = seed_initial_cases_if_needed(session)
            if seeded_count > 0:
                logger.info("Initialized database with %d canonical cases.", seeded_count)
        finally:
            session.close()
    except Exception as e:
        logger.error("Failed to seed initial demo cases: %s", e)

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


import os
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Static Files & SPA Frontend Serving (when dist/ is built)
dist_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "dist"))
if os.path.exists(dist_path):
    assets_path = os.path.join(dist_path, "assets")
    if os.path.exists(assets_path):
        app.mount("/assets", StaticFiles(directory=assets_path), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        # Allow API docs / OpenAPI schema
        if full_path in ("docs", "redoc", "openapi.json"):
            return None
        file_path = os.path.join(dist_path, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_file = os.path.join(dist_path, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"error": "Frontend build not found"}


