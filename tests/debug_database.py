import asyncio
import sys
import os

# Add the parent directory to the Python path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import init_db, close_db, fetch_one, execute_query

async def debug_database():
    """Debug what's actually in the database"""
    
    try:
        print("🔧 Initializing database connection...")
        await init_db()
        print("✅ Database connection initialized successfully")
        
        print("\n📊 Checking database contents...")
        
        # Check total conversations
        result = await fetch_one("SELECT COUNT(*) as count FROM conversation")
        total_conversations = result["count"] if result else 0
        print(f"Total conversations in database: {total_conversations}")
        
        if total_conversations > 0:
            print("\n📋 Recent conversations (last 5):")
            # Get recent conversations
            query = """
                SELECT 
                    id, 
                    ai_intent_summary, 
                    is_qualified, 
                    source, 
                    status,
                    created_at
                FROM conversation 
                ORDER BY created_at DESC 
                LIMIT 5
            """
            
            # Since fetch_one only gets one result, let's use execute_query differently
            # Let's try a different approach to get multiple results
            try:
                result = await fetch_one(query)
                if result:
                    print(f"✅ Found conversation:")
                    print(f"   ID: {result['id']}")
                    print(f"   AI Summary: {result['ai_intent_summary'][:100]}..." if result['ai_intent_summary'] else "None")
                    print(f"   Is Qualified: {result['is_qualified']}")
                    print(f"   Status: {result['status']}")
                    print(f"   Created: {result['created_at']}")
                    
                    # Test exact match search
                    print(f"\n🔍 Testing exact match search with this summary...")
                    search_result = await fetch_one(
                        "SELECT * FROM conversation WHERE ai_intent_summary = $1", 
                        result['ai_intent_summary']
                    )
                    if search_result:
                        print("✅ Exact match search works!")
                    else:
                        print("❌ Exact match search failed!")
                        
                    # Test LIKE search
                    print(f"\n🔍 Testing LIKE search...")
                    like_result = await fetch_one(
                        "SELECT * FROM conversation WHERE ai_intent_summary LIKE $1", 
                        f"%apartment%"
                    )
                    if like_result:
                        print("✅ LIKE search works!")
                    else:
                        print("❌ LIKE search failed!")
                        
            except Exception as e:
                print(f"❌ Error querying conversations: {e}")
        
        # Check messages table for unanswered questions
        result = await fetch_one("SELECT COUNT(*) as count FROM message WHERE message_type = 'unanswered_question'")
        unanswered_count = result["count"] if result else 0
        print(f"\nUnanswered questions in database: {unanswered_count}")
        
        if unanswered_count > 0:
            print("\n❓ Recent unanswered questions:")
            question_result = await fetch_one("""
                SELECT message_text, timestamp, metadata 
                FROM message 
                WHERE message_type = 'unanswered_question' 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            if question_result:
                print(f"   Question: {question_result['message_text']}")
                print(f"   Timestamp: {question_result['timestamp']}")
                print(f"   Metadata: {question_result['metadata']}")
        
        print("\n🔍 Debugging complete!")
        
    except Exception as e:
        print(f"❌ Error during debugging: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔒 Closing database connection...")
        await close_db()
        print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(debug_database()) 