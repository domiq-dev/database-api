"""
Check imported companies in the database
"""

import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def check_companies():
    """Check the imported companies"""
    
    engine = create_async_engine(DATABASE_URL)
    
    async with engine.connect() as conn:
        # Check total count
        result = await conn.execute(text("SELECT COUNT(*) FROM company"))
        count = result.scalar()
        print(f"Total companies in database: {count}")
        
        # Check recent imports
        result = await conn.execute(text("""
            SELECT name, contact_email, hubspot_company_id, created_at 
            FROM company 
            ORDER BY created_at DESC 
            LIMIT 10
        """))
        
        companies = result.fetchall()
        print("\nRecent companies:")
        for company in companies:
            print(f"- {company.name} ({company.contact_email}) - {company.hubspot_company_id}")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_companies()) 