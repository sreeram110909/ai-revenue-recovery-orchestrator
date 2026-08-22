"""SQLAlchemy Database Engine & Session Factory.

PostgreSQL is the intended production database.
SQLite is used ONLY as a local-development/testing fallback when DATABASE_URL is not set.
The engine is never silently switched in production — the /health endpoint reports which
database backend is active.
"""

import logging
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from .config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    """SQLAlchemy declarative base for all ORM models."""
    pass


def create_db_engine():
    """Create SQLAlchemy engine using Settings.

    - If DATABASE_URL is set → PostgreSQL (intended for production/demo).
    - If DATABASE_URL is empty → SQLite fallback (local development only).
    """
    settings = get_settings()
    db_url = settings.effective_database_url
    is_sqlite = settings.is_sqlite_fallback

    if is_sqlite:
        logger.warning(
            "DATABASE_URL is not set. Using SQLite fallback: %s. "
            "This is for local development only. "
            "Set DATABASE_URL for production/demo deployment.",
            db_url,
        )
        engine = create_engine(
            db_url,
            connect_args={"check_same_thread": False},
            echo=(settings.environment == "development"),
        )
        # Enable WAL mode for better concurrent read performance in SQLite
        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    else:
        logger.info("Using PostgreSQL database: %s", db_url.split("@")[-1] if "@" in db_url else "(configured)")
        engine = create_engine(
            db_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            echo=(settings.environment == "development"),
        )

    return engine


def create_tables(engine):
    """Create all ORM tables. Called at application startup."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created/verified.")


def get_session_factory(engine):
    """Create a session factory bound to the given engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


_engine = None
_SessionFactory = None


def get_db_session():
    """FastAPI dependency providing a SQLAlchemy database session per request."""
    global _engine, _SessionFactory
    if _SessionFactory is None:
        _engine = create_db_engine()
        _SessionFactory = get_session_factory(_engine)
        create_tables(_engine)

    session = _SessionFactory()
    try:
        yield session
    finally:
        session.close()
