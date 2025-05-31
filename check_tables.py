"""
Check what tables actually exist in the database
"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

async def check_tables():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    try:
        engine = create_async_engine(database_url)
        
        async with engine.begin() as conn:
            # Get all table names
            result = await conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name
            """))
            
            tables = result.fetchall()
            print("Tables in database:")
            for table in tables:
                print(f"  - {table[0]}")
                
            # Check company table structure
            if any('company' in str(table) for table in tables):
                print("\nCompany table columns:")
                result = await conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'company'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                for col in columns:
                    print(f"  - {col[0]} ({col[1]}) {'NULL' if col[2] == 'YES' else 'NOT NULL'}")
                    
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(check_tables()) 