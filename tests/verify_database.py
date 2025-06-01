import asyncio
import sys
import os

# Add the parent directory to the Python path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import db_service
from config.database import init_db, close_db, fetch_one

async def verify_database():
    """Verify that data was saved to the database"""
    
    try:
        print("🔧 Initializing database connection...")
        await init_db()
        print("✅ Database connection initialized successfully")
        
        print("\n📊 Database Summary:")
        
        # Get total counts
        conv_result = await fetch_one("SELECT COUNT(*) as count FROM conversation")
        msg_result = await fetch_one("SELECT COUNT(*) as count FROM message WHERE message_type = 'unanswered_question'")
        
        total_conversations = conv_result["count"] if conv_result else 0
        total_questions = msg_result["count"] if msg_result else 0
        
        print(f"   Total Conversations: {total_conversations}")
        print(f"   Total Unanswered Questions: {total_questions}")
        
        print("\n📄 Recent conversations...")
        
        # Get the most recent conversation
        recent_conv = await fetch_one("""
            SELECT 
                id, 
                ai_intent_summary, 
                is_qualified, 
                source, 
                status,
                created_at
            FROM conversation 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        
        if recent_conv:
            print("✅ Found recent conversation:")
            print(f"   ID: {recent_conv['id']}")
            print(f"   AI Summary: {recent_conv['ai_intent_summary'][:150]}...")
            print(f"   Is Qualified: {recent_conv['is_qualified']}")
            print(f"   Status: {recent_conv['status']}")
            print(f"   Created: {recent_conv['created_at']}")
            
            # Test the database service search function with the actual summary
            print(f"\n🔍 Testing database service search...")
            found_conversation = await db_service.get_conversation_by_summary(recent_conv['ai_intent_summary'])
            
            if found_conversation:
                print("✅ Database service search works correctly!")
                print(f"   Retrieved ID: {found_conversation['id']}")
            else:
                print("❌ Database service search failed!")
        else:
            print("❌ No conversations found in database")
            
        print("\n❓ Checking for unanswered questions...")
        
        questions = await db_service.get_unanswered_questions(10)
        
        if questions:
            print(f"✅ Found {len(questions)} unanswered question(s):")
            for i, question in enumerate(questions, 1):
                print(f"   {i}. {question.get('question', 'N/A')}")
                print(f"      Timestamp: {question.get('timestamp', 'N/A')}")
        else:
            print("ℹ️  No unanswered questions found")
            
        # Test LIKE search for apartments
        print(f"\n🔍 Testing LIKE search for 'apartment'...")
        apartment_conv = await fetch_one("""
            SELECT id, ai_intent_summary, is_qualified
            FROM conversation 
            WHERE ai_intent_summary LIKE $1
            ORDER BY created_at DESC 
            LIMIT 1
        """, "%apartment%")
        
        if apartment_conv:
            print("✅ LIKE search for 'apartment' works!")
            print(f"   Found conversation: {apartment_conv['ai_intent_summary'][:100]}...")
        else:
            print("❌ LIKE search for 'apartment' failed!")
            
        print("\n✅ Database verification completed!")
        
    except Exception as e:
        print(f"❌ Error during verification: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔒 Closing database connection...")
        await close_db()
        print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(verify_database()) 