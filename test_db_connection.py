"""
Simple database connection test
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

async def test_connection():
    load_dotenv()
    
    # Get database URL
    database_url = os.getenv("DATABASE_URL")
    print(f"Testing connection to: {database_url}")
    
    try:
        # Create engine
        engine = create_async_engine(database_url)
        
        # Test simple query
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT 1"))
            print("✅ Database connection successful!")
            print(f"Result: {result.fetchone()}")
            
        # Test if company table exists
        async with engine.begin() as conn:
            result = await conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name = 'company'"))
            table_exists = result.fetchone()
            if table_exists:
                print("✅ Company table exists")
            else:
                print("❌ Company table does NOT exist")
                
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_connection()) 