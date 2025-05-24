import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def setup_test_data():
    """Create all necessary test data in the database"""

    engine = create_async_engine(DATABASE_URL)

    async with engine.begin() as conn:
        print("Setting up test data...")

        # Create a test company (if needed by your schema)
        await conn.execute(text("""
            INSERT INTO company (id, name, contact_email, created_at, updated_at)
            VALUES (
                '550e8400-e29b-41d4-a716-446655440099'::uuid,
                'Test Property Management Company',
                'admin@testcompany.com',
                NOW(),
                NOW()
            ) ON CONFLICT (id) DO NOTHING
        """))

        # Create a test property
        await conn.execute(text("""
            INSERT INTO property (
                id,
                company_id,
                name,
                address,
                city,
                state,
                zip_code,
                property_type,
                units_count,
                created_at,
                updated_at
            ) VALUES (
                '550e8400-e29b-41d4-a716-446655440000'::uuid,
                '550e8400-e29b-41d4-a716-446655440099'::uuid,
                'Sunset Apartments',
                '123 Main St',
                'Chapel Hill',
                'NC',
                '27514',
                'apartment',
                100,
                NOW(),
                NOW()
            ) ON CONFLICT (id) DO NOTHING
        """))

        # Create a test chatbot
        await conn.execute(text("""
            INSERT INTO chatbot (
                id,
                property_id,
                name,
                is_active,
                welcome_message,
                created_at,
                updated_at
            ) VALUES (
                '550e8400-e29b-41d4-a716-446655440001'::uuid,
                '550e8400-e29b-41d4-a716-446655440000'::uuid,
                'Sunset Apartments Assistant',
                true,
                'Welcome! How can I help you find your perfect apartment at Sunset Apartments?',
                NOW(),
                NOW()
            ) ON CONFLICT (id) DO NOTHING
        """))

        # Create a test user
        await conn.execute(text("""
            INSERT INTO "user" (
                id, 
                first_name, 
                last_name, 
                email, 
                phone, 
                age, 
                lead_source,
                created_at,
                updated_at
            ) VALUES (
                '550e8400-e29b-41d4-a716-446655440002'::uuid,
                'John',
                'Doe',
                'john.doe@example.com',
                '555-1234',
                30,
                'Facebook Ads',
                NOW(),
                NOW()
            ) ON CONFLICT (id) DO NOTHING
        """))

        print("Test data setup complete!")
        print("\nYou can now use these IDs in your API calls:")
        print("chatbot_id: 550e8400-e29b-41d4-a716-446655440001")
        print("user_id: 550e8400-e29b-41d4-a716-446655440002")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(setup_test_data())