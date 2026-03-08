import os
from typing import AsyncGenerator, Any
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import logging

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

# Database URL from environment variable
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL not found in environment variables. "
        "Please create a .env file with DATABASE_URL or set it as an environment variable."
    )

# Create async engine
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Configure timezone on connection
@event.listens_for(engine.sync_engine, "connect")
def set_timezone(dbapi_conn, connection_record):
    """Set connection timezone to UTC"""
    cursor = dbapi_conn.cursor()
    cursor.execute("SET TIME ZONE 'UTC'")
    cursor.close()

# Session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base for ORM models
Base = declarative_base()

# Initialize database
async def init_db():
    """
    Initialize database tables
    Auto-creates all tables defined in Base metadata
    """
    logger.info("Initializing database...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database initialized successfully")
    except Exception as e:
        logger.error(f"✗ Error initializing database: {str(e)}")
        raise

# Close database connections
async def close_db():
    """Close database connections gracefully"""
    logger.info("Closing database connections...")
    await engine.dispose()
    logger.info("✓ Database connections closed")

# Dependency for FastAPI
async def get_db_session() -> AsyncGenerator[AsyncSession, Any]:
    """
    FastAPI dependency to get database session
    Automatically handles session lifecycle
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()