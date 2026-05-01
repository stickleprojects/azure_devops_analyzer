"""
Database connection management.

Provides SQLAlchemy engine creation and session management with connection pooling.
"""

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def get_database_url() -> str:
    """
    Build database URL from environment variables.

    Supports either DATABASE_URL or individual POSTGRES_* variables.
    """
    database_url = os.environ.get("DATABASE_URL")
    if database_url:
        return database_url

    host = os.environ.get("POSTGRES_HOST", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    user = os.environ.get("POSTGRES_USER", "postgres")
    password = os.environ.get("POSTGRES_PASSWORD", "postgres")
    database = os.environ.get("POSTGRES_DB", "repo_analyzer")

    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


_engine: Engine | None = None


def get_engine() -> Engine:
    """
    Get or create the SQLAlchemy engine with connection pooling.

    Returns:
        Configured SQLAlchemy Engine instance.
    """
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
    return _engine


SessionLocal = sessionmaker(autocommit=False, autoflush=False)


def get_session() -> Session:
    """
    Create a new database session.

    The session is bound to the engine on first use.

    Returns:
        New SQLAlchemy Session instance.
    """
    SessionLocal.configure(bind=get_engine())
    return SessionLocal()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """
    Context manager for database sessions with automatic commit/rollback.

    Usage:
        with session_scope() as session:
            session.add(obj)
            # auto-commits on success, rolls back on exception

    Yields:
        Database session.
    """
    session = get_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
