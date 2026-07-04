from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase
from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncSession:
    """FastAPI dependency — yields a DB session per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def create_tables() -> None:
    """Called on startup to create all tables."""
    async with engine.begin() as conn:
        from app.models import models  # noqa: F401 — import to register models
        await conn.run_sync(Base.metadata.create_all)


async def sync_schema() -> None:
    """Add columns that create_all does not apply to existing SQLite tables."""
    async with engine.begin() as conn:
        def _missing_columns(connection):
            inspector = inspect(connection)
            table_names = inspector.get_table_names()
            plan = []

            if "cv_uploads" in table_names:
                existing = {col["name"] for col in inspector.get_columns("cv_uploads")}
                expected = {"best_fit_role": "VARCHAR(255)"}
                plan += [
                    ("cv_uploads", name, col_type)
                    for name, col_type in expected.items()
                    if name not in existing
                ]

            if "interview_sessions" in table_names:
                existing = {col["name"] for col in inspector.get_columns("interview_sessions")}
                expected = {"cv_report": "TEXT"}
                plan += [
                    ("interview_sessions", name, col_type)
                    for name, col_type in expected.items()
                    if name not in existing
                ]

            return plan

        missing = await conn.run_sync(_missing_columns)
        for table_name, column_name, column_type in missing:
            await conn.execute(
                text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
            )