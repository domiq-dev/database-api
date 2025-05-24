"""
Property Management Chatbot - Database Configuration

This module configures the database connection and session management for the
property management chatbot system. It uses SQLAlchemy's async engine for
non-blocking database operations, which is essential for high-performance
web applications.

Key Features:
- Async database operations for better performance
- Environment-based configuration for different deployment environments
- Connection pooling and session management
- Dependency injection pattern for FastAPI integration

Database Requirements:
- PostgreSQL 12+ (for UUID and JSON support)
- Async driver (asyncpg) for optimal performance
- Connection string format: postgresql+asyncpg://user:pass@host:port/db

Author: Development Team
Created: 2024
Last Modified: 2024
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
# This allows for different configurations in development, staging, and production
load_dotenv()

# Get DATABASE_URL from environment variable
# Format: postgresql+asyncpg://username:password@host:port/database_name
DATABASE_URL = os.getenv("DATABASE_URL")

# Validate that DATABASE_URL is configured
# This prevents runtime errors and provides clear error messages
if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Please set it in your .env file or environment. "
        "Format: postgresql+asyncpg://user:password@host:port/database"
    )

# Create async database engine
# echo=True enables SQL query logging for debugging (disable in production)
engine = create_async_engine(
    DATABASE_URL, 
    echo=True,  # Set to False in production for better performance
    # Additional engine options can be added here:
    # pool_size=20,          # Connection pool size
    # max_overflow=0,        # Additional connections beyond pool_size
    # pool_pre_ping=True,    # Validate connections before use
    # pool_recycle=3600,     # Recycle connections after 1 hour
)

# Create async session factory
# expire_on_commit=False prevents lazy loading issues with async sessions
async_session = sessionmaker(
    engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_db():
    """
    Database dependency for FastAPI dependency injection
    
    This function provides database sessions to FastAPI route handlers.
    It ensures proper session lifecycle management with automatic cleanup.
    
    The session is automatically closed when the request completes,
    preventing connection leaks and ensuring database resources are
    properly released.
    
    Usage in FastAPI routes:
        @router.post("/endpoint/")
        async def my_endpoint(db: AsyncSession = Depends(get_db)):
            # Use db session here
            result = await db.execute(query)
            return result
    
    Yields:
        AsyncSession: Database session for the current request
        
    Note:
        This is a generator function that yields the session and ensures
        cleanup happens after the request completes, even if an exception occurs.
    """
    # Create a new session for this request
    async with async_session() as session:
        try:
            # Yield the session to the route handler
            yield session
        finally:
            # Session is automatically closed by the context manager
            # This ensures proper cleanup even if an exception occurs
            pass