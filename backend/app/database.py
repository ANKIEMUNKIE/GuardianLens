"""
GuardianLens — Database
Async SQLAlchemy engine — SQLite by default, PostgreSQL via DATABASE_URL env var
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(
    str(settings.DATABASE_URL),
    echo=settings.APP_ENV == "development",
    future=True,
    connect_args={"check_same_thread": False} if "sqlite" in str(settings.DATABASE_URL) else {},
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """FastAPI dependency — yields an async DB session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables on startup."""
    async with engine.begin() as conn:
        from app.models import scan  # noqa: F401 — ensure models are imported
        await conn.run_sync(Base.metadata.create_all)
