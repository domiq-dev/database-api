import os
import asyncpg
from typing import Optional
from dotenv import load_dotenv
import asyncio
import ssl

# Load environment variables
load_dotenv()

# Get database configuration from environment variables
DB_HOST = os.getenv('PG_HOST')
DB_PORT = os.getenv('PG_PORT')
DB_NAME = os.getenv('PG_DATABASE')
DB_USER = os.getenv('PG_USER')
DB_PASSWORD = os.getenv('PG_PASSWORD')

# Debug print to verify configuration
print("Database Configuration:")
print(f"Host: {DB_HOST}")
print(f"Port: {DB_PORT}")
print(f"Database: {DB_NAME}")
print(f"User: {DB_USER}")

# Validate that all required variables are set
if not all([DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD]):
    raise ValueError("Missing required database environment variables")

# Connection pool
_pool: Optional[asyncpg.Pool] = None

def get_pool() -> asyncpg.Pool:
    """Get the database connection pool"""
    if _pool is None:
        raise RuntimeError("Database connection pool not initialized")
    return _pool

async def init_db():
    """Initialize database connection pool"""
    global _pool
    try:
        # SSL context for RDS
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE

        _pool = await asyncpg.create_pool(
            host=DB_HOST,
            port=DB_PORT,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            min_size=5,  # Minimum number of connections
            max_size=20,  # Maximum number of connections
            command_timeout=60,  # Command timeout in seconds
            statement_cache_size=100,  # Number of statements to cache
            max_cached_statement_lifetime=300,  # Cache lifetime in seconds
            ssl=ssl_context,  # SSL configuration for RDS
            server_settings={
                'application_name': 'ava_leasing_chatbot'  # Identify the application
            }
        )
        print("✅ Database connection pool initialized")
    except Exception as e:
        print(f"❌ Error initializing database connection pool: {e}")
        raise

async def close_db():
    """Close database connection pool"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("✅ Database connection pool closed")

async def get_connection():
    """Get a database connection from the pool"""
    pool = get_pool()
    try:
        return await pool.acquire()
    except Exception as e:
        print(f"❌ Error acquiring database connection: {e}")
        raise

async def release_connection(conn):
    """Release a database connection back to the pool"""
    pool = get_pool()
    await pool.release(conn)

async def execute_query(query: str, *args):
    """Execute a database query with error handling and retries"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ Error executing query after {max_retries} attempts: {e}")
                raise
            print(f"⚠️ Query failed (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff

async def fetch_one(query: str, *args):
    """Fetch a single row from the database"""
    max_retries = 3
    retry_delay = 1  # seconds
    
    for attempt in range(max_retries):
        try:
            pool = get_pool()
            async with pool.acquire() as conn:
                return await conn.fetchrow(query, *args)
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"❌ Error fetching row after {max_retries} attempts: {e}")
                raise
            print(f"⚠️ Fetch failed (attempt {attempt + 1}/{max_retries}): {e}")
            await asyncio.sleep(retry_delay)
            retry_delay *= 2  # Exponential backoff 