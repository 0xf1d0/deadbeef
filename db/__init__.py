"""
Database initialization with improved configuration and error handling.
"""
from sqlalchemy import create_engine, event
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
import os
import logging
from typing import AsyncGenerator

from .models import Base

# Configure logging
logger = logging.getLogger(__name__)

# Database configuration
DB_DIR = os.path.join(os.path.dirname(__file__), '..')
DB_PATH = os.path.join(DB_DIR, 'database.db')
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{DB_PATH}")

# SQLite-specific optimizations
SQLITE_PRAGMAS = {
    'journal_mode': 'WAL',  # Write-Ahead Logging for better concurrency
    'cache_size': -64000,   # 64MB cache
    'foreign_keys': 1,      # Enable foreign key constraints
    'synchronous': 'NORMAL', # Balance between safety and speed
}


def configure_sqlite_connection(dbapi_conn, connection_record):
    """Configure SQLite connection with optimizations."""
    cursor = dbapi_conn.cursor()
    for pragma, value in SQLITE_PRAGMAS.items():
        cursor.execute(f"PRAGMA {pragma}={value}")
    cursor.close()


# Create async engine with optimizations
engine = create_async_engine(
    DATABASE_URL,
    echo=False,  # Set to True for SQL debugging
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,
    max_overflow=10,
    pool_recycle=3600,  # Recycle connections after 1 hour
)

# Register SQLite optimization callback
if 'sqlite' in DATABASE_URL:
    event.listen(engine.sync_engine, "connect", configure_sqlite_connection)

# Create async session maker
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,  # Manual flush control for better performance
)


async def init_db() -> None:
    """
    Initialize the database by creating all tables.
    Safe to call multiple times - will only create missing tables/indexes.
    
    Raises:
        Exception: If database initialization fails
    """
    try:
        async with engine.begin() as conn:
            # Create all tables and indexes
            # checkfirst=True is default, but we catch OperationalError for existing indexes
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            logger.info("Database initialized successfully")
    except Exception as e:
        # If the error is about indexes already existing, that's fine - database is already set up
        error_msg = str(e).lower()
        if 'already exists' in error_msg or 'duplicate' in error_msg:
            logger.info("Database already initialized (indexes exist)")
        else:
            logger.error(f"Failed to initialize database: {e}")
            raise


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Get a database session with proper error handling.
    
    Yields:
        AsyncSession: Database session
    
    Usage:
        async with get_session() as session:
            # Use session
            pass
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception as e:
            await session.rollback()
            logger.error(f"Session error: {e}")
            raise
        finally:
            await session.close()


async def close_db() -> None:
    """
    Close database connections gracefully.
    Call this during bot shutdown.
    """
    try:
        await engine.dispose()
        logger.info("Database connections closed")
    except Exception as e:
        logger.error(f"Error closing database: {e}")


# Health check function
async def check_db_health() -> bool:
    """
    Check if database is accessible and healthy.
    
    Returns:
        bool: True if database is healthy, False otherwise
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute("SELECT 1")
            return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False

