"""
GuardianLens — Database
Async SQLAlchemy engine — SQLite by default, PostgreSQL via DATABASE_URL env var
"""
import logging
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


def _make_engine():
    db_url = str(settings.DATABASE_URL)
    kwargs = {"echo": settings.APP_ENV == "development", "future": True}
    if "sqlite" in db_url:
        kwargs["connect_args"] = {"check_same_thread": False}
    return create_async_engine(db_url, **kwargs)


try:
    engine = _make_engine()
except Exception as e:
    logger.warning(f"DB engine creation failed at import: {e} — will retry on first request")
    engine = None


def get_engine():
    global engine
    if engine is None:
        engine = _make_engine()
    return engine


def get_session_factory():
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
    )


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    factory = get_session_factory()
    async with factory() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    try:
        eng = get_engine()
        async with eng.begin() as conn:
            from app.models import scan  # noqa: F401 — ensure models are imported
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created/verified ✓")
    except Exception as e:
        logger.error(f"DB init failed: {e} — app will continue in degraded mode")
