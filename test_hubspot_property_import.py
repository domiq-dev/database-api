"""
Test HubSpot Property Import
"""
import asyncio
import aiofiles
from app.routers.hubspot_property import PropertyCSVProcessor
from app.db import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from dotenv import load_dotenv

async def test_property_import():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    try:
        engine = create_async_engine(database_url)
        
        async with AsyncSession(engine) as db:
            # Read the CSV file
            async with aiofiles.open("hubspot-form-submissions-property-updating-form-2025-05-29-1.csv", "r") as f:
                file_content = await f.read()
            
            # Process the CSV
            processor = PropertyCSVProcessor(db)
            results = await processor.process_csv_file(file_content)
            
            print("✅ Property import results:")
            print(f"  Processed: {results['processed']}")
            print(f"  Created: {results['created']}")
            print(f"  Updated: {results['updated']}")
            print(f"  Errors: {results['errors']}")
            
            if results['error_details']:
                print("\nError details:")
                for error in results['error_details']:
                    print(f"  Row {error['row']}: {error['error']}")
                    
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_property_import()) 