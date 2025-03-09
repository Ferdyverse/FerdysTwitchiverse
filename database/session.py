from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from .base import Base  # Import Base to register models

DATABASE_URL = "sqlite+aiosqlite:///./storage/data.db"

# Create an asynchronous engine for SQLite
async_engine = create_async_engine(DATABASE_URL, echo=True)

# Define an asynchronous session factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency function for FastAPI routes
async def get_db():
    """Provide an async database session using dependency injection."""
    async with AsyncSessionLocal() as session:
        yield session

# Initialize the database asynchronously
async def init_db():
    """Create all database tables asynchronously using the registered models."""
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
