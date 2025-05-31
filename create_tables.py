"""
Create database tables for the models
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.models import Base
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def create_tables():
    """Create all database tables"""
    
    print("Creating database tables...")
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    await engine.dispose()
    print("✅ Database tables created successfully!")

if __name__ == "__main__":
    asyncio.run(create_tables()) 