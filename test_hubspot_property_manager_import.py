"""
Test HubSpot Property Manager Import
"""
import asyncio
import aiofiles
from app.routers.hubspot_property_manager import PropertyManagerCSVProcessor
from app.db import get_db
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
import os
from dotenv import load_dotenv

async def test_property_manager_import():
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    try:
        engine = create_async_engine(database_url)
        
        async with AsyncSession(engine) as db:
            # Read the CSV file
            async with aiofiles.open("hubspot-form-submissions-manager-onboarding-form-2025-05-29-2.csv", "r") as f:
                file_content = await f.read()
            
            # Process the CSV
            processor = PropertyManagerCSVProcessor(db)
            results = await processor.process_csv_file(file_content)
            
            print("✅ Property Manager import results:")
            print(f"  Processed: {results['processed']}")
            print(f"  Created: {results['created']}")
            print(f"  Updated: {results['updated']}")
            print(f"  Assignments Created: {results['assignments_created']}")
            print(f"  Errors: {results['errors']}")
            
            if results['error_details']:
                print("\nError details:")
                for error in results['error_details']:
                    print(f"  Row {error['row']}: {error['error']}")
                    
        await engine.dispose()
        
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_property_manager_import()) 