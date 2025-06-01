import asyncio
import sys
import os

# Add the parent directory to the Python path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import init_db, close_db
from services.db_service import db_service

async def test_db_service():
    """Test the database service functionality"""
    
    try:
        print("🔧 Initializing database connection...")
        await init_db()
        print("✅ Database connection initialized successfully")
        
        # Test data
        test_conversation_id = "test_conv_123"
        test_ai_summary = "User inquired about 2-bedroom apartments, expressed interest in touring next week"
        test_is_qualified = True
        test_kb_pending = "What are the pet fees for large dogs?"
        
        print("\n📝 Testing conversation save...")
        
        # Test saving a conversation
        success = await db_service.save_conversation_with_unanswered_question(
            conversation_id=test_conversation_id,
            ai_intent_summary=test_ai_summary,
            is_qualified=test_is_qualified,
            kb_pending=test_kb_pending,
            source="LLM",
            status="completed"
        )
        
        if success:
            print("✅ Successfully saved conversation and unanswered question")
        else:
            print("❌ Failed to save conversation and unanswered question")
            
        print("\n📄 Testing conversation retrieval...")
        
        # Test retrieving the conversation
        conversation = await db_service.get_conversation_by_summary(test_ai_summary)
        
        if conversation:
            print("✅ Successfully retrieved conversation:")
            print(f"   ID: {conversation['id']}")
            print(f"   AI Summary: {conversation['ai_intent_summary']}")
            print(f"   Is Qualified: {conversation['is_qualified']}")
            print(f"   Status: {conversation['status']}")
            print(f"   Source: {conversation['source']}")
        else:
            print("❌ Failed to retrieve conversation")
            
        print("\n❓ Testing unanswered questions retrieval...")
        
        # Test retrieving unanswered questions
        questions = await db_service.get_unanswered_questions(limit=10)
        
        if questions:
            print(f"✅ Retrieved {len(questions)} unanswered question(s):")
            for question in questions:
                print(f"   Question: {question.get('question', 'N/A')}")
                print(f"   Timestamp: {question.get('timestamp', 'N/A')}")
        else:
            print("ℹ️  No unanswered questions found (or retrieval failed)")
            
        print("\n🔄 Testing status update...")
        
        # Test updating conversation status
        update_success = await db_service.update_conversation_status(
            ai_intent_summary=test_ai_summary,
            status="follow_up_needed",
            is_qualified=True
        )
        
        if update_success:
            print("✅ Successfully updated conversation status")
        else:
            print("❌ Failed to update conversation status")
            
        print("\n✅ All database service tests completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔒 Closing database connection...")
        await close_db()
        print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_db_service()) 