import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os
from dotenv import load_dotenv
from datetime import datetime
import json

# Load environment variables
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def get_database_overview():
    """Get a complete helicopter view of the database"""

    engine = create_async_engine(DATABASE_URL)

    async with engine.connect() as conn:
        print("=" * 80)
        print("DATABASE HELICOPTER VIEW")
        print("=" * 80)
        print(f"Generated at: {datetime.now()}")
        print("=" * 80)

        # 1. Table Summary
        print("\n📊 TABLE SUMMARY")
        print("-" * 40)

        tables = ['company', 'property', 'chatbot', '"user"', 'conversation', 'message',
                  'lead_notification', 'property_manager', 'property_manager_assignment']

        for table in tables:
            result = await conn.execute(text(f"SELECT COUNT(*) as count FROM {table}"))
            count = result.scalar()
            print(f"{table:<30} {count:>10} rows")

        # 2. Conversation Statistics
        print("\n📈 CONVERSATION STATISTICS")
        print("-" * 40)

        stats_query = """
        SELECT 
            COUNT(*) as total_conversations,
            COUNT(CASE WHEN is_qualified = true THEN 1 END) as qualified_leads,
            COUNT(CASE WHEN is_book_tour = true THEN 1 END) as tours_booked,
            COUNT(CASE WHEN status = 'new' THEN 1 END) as new_status,
            COUNT(CASE WHEN status = 'qualified' THEN 1 END) as qualified_status,
            COUNT(CASE WHEN status = 'tour_scheduled' THEN 1 END) as tour_scheduled_status,
            AVG(lead_score) as avg_lead_score,
            MAX(lead_score) as max_lead_score
        FROM conversation
        """

        result = await conn.execute(text(stats_query))
        stats = result.fetchone()

        print(f"Total Conversations:    {stats.total_conversations}")
        print(f"Qualified Leads:        {stats.qualified_leads}")
        print(f"Tours Booked:          {stats.tours_booked}")
        print(f"Status - New:          {stats.new_status}")
        print(f"Status - Qualified:    {stats.qualified_status}")
        print(f"Status - Tour Scheduled: {stats.tour_scheduled_status}")
        print(f"Max Lead Score:        {stats.max_lead_score}")

        # 3. Recent Activity
        print("\n🕐 RECENT ACTIVITY (Last 5 Conversations)")
        print("-" * 80)

        recent_query = """
        SELECT 
            c.created_at,
            c.id,
            COALESCE(u.email, 'Anonymous') as user_email,
            c.ai_intent_summary,
            c.status,
            c.lead_score
        FROM conversation c
        LEFT JOIN "user" u ON c.user_id = u.id
        ORDER BY c.created_at DESC
        LIMIT 5
        """

        result = await conn.execute(text(recent_query))
        recent = result.fetchall()

        for row in recent:
            print(f"\n{row.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"  ID: {row.id}")
            print(f"  User: {row.user_email}")
            print(f"  Intent: {row.ai_intent_summary}")
            print(f"  Status: {row.status} | Score: {row.lead_score}")

        # 4. User Analysis
        print("\n👥 USER ANALYSIS")
        print("-" * 40)

        user_query = """
        SELECT 
            COUNT(*) as total_users,
            COUNT(CASE WHEN email IS NOT NULL THEN 1 END) as with_email,
            COUNT(CASE WHEN phone IS NOT NULL THEN 1 END) as with_phone,
            COUNT(CASE WHEN email IS NULL AND phone IS NULL THEN 1 END) as anonymous
        FROM "user"
        """

        result = await conn.execute(text(user_query))
        users = result.fetchone()

        print(f"Total Users:        {users.total_users}")
        print(f"With Email:         {users.with_email}")
        print(f"With Phone:         {users.with_phone}")
        print(f"Anonymous:          {users.anonymous}")

        # 5. Data Quality Check
        print("\n✅ DATA QUALITY CHECK")
        print("-" * 40)

        # Check for orphaned records
        orphan_conversations = await conn.execute(text("""
            SELECT COUNT(*) FROM conversation c
            LEFT JOIN chatbot cb ON c.chatbot_id = cb.id
            WHERE cb.id IS NULL
        """))
        print(f"Orphaned conversations (no chatbot): {orphan_conversations.scalar()}")

        orphan_users = await conn.execute(text("""
            SELECT COUNT(*) FROM conversation c
            LEFT JOIN "user" u ON c.user_id = u.id
            WHERE u.id IS NULL
        """))
        print(f"Orphaned conversations (no user):   {orphan_users.scalar()}")

        # 6. Full Data Dump (Optional)
        print("\n📋 FULL CONVERSATION DETAILS")
        print("-" * 80)

        full_query = """
        SELECT 
            c.*,
            u.email as user_email,
            u.first_name,
            u.last_name,
            cb.name as chatbot_name
        FROM conversation c
        LEFT JOIN "user" u ON c.user_id = u.id
        LEFT JOIN chatbot cb ON c.chatbot_id = cb.id
        ORDER BY c.created_at DESC
        """

        result = await conn.execute(text(full_query))
        conversations = result.fetchall()

        print(f"\nTotal conversations in database: {len(conversations)}")
        print("\nShow full details? (y/n): ", end='')

        if input().lower() == 'y':
            for conv in conversations:
                print(f"\n{'=' * 60}")
                for key in result.keys():
                    value = getattr(conv, key)
                    if value is not None:
                        print(f"{key}: {value}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(get_database_overview())