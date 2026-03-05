"""SQLite database setup with SQLAlchemy."""

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from datetime import datetime
import os

# Database URL - uses SQLite with aiosqlite for async support
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./recipes.db")

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True to see SQL queries
    future=True,
    pool_pre_ping=True,
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)

# Base class for models
Base = declarative_base()


class RecipeModel(Base):
    """SQLAlchemy model for recipes."""
    
    __tablename__ = "recipes"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), index=True, nullable=False)
    description = Column(Text, nullable=True)
    ingredients = Column(JSON, nullable=False)  # Store as JSON array
    instructions = Column(Text, nullable=False)
    prep_time = Column(Integer, nullable=True)  # in minutes
    cook_time = Column(Integer, nullable=True)  # in minutes
    category = Column(String(100), index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)


async def init_db():
    """Initialize database tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_db():
    """Dependency for getting database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
