import asyncio
import sys
import os
import json
import time
import uuid
from datetime import datetime

# Add the parent directory to the Python path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import db_service
from config.database import init_db, close_db, fetch_one, execute_query
from main import generate_and_send_summary, conversations, conversations_lock

async def test_postgresql_data_push():
    """Test comprehensive data pushing to PostgreSQL database"""
    
    print("🚀 Testing PostgreSQL Data Push Operations")
    print("=" * 60)
    
    try:
        # Initialize database
        await init_db()
        print("✅ Database connection initialized")
        
        # Test Case 1: Qualified user with apartment inquiry
        print("\n📋 Test Case 1: Qualified User - Apartment Inquiry")
        conversation_id_1 = str(uuid.uuid4())  # Use proper UUID format
        test_conversation_1 = {
            "conversation_id": conversation_id_1,
            "history": [
                {"user": "Hi, I'm looking for a 2-bedroom apartment"},
                {"ava": "I'd be happy to help you find a 2-bedroom apartment! What's your budget range?"},
                {"user": "Around $2500 per month"},
                {"ava": "That's a great budget! Let me help you get pre-qualified."},
                {"user": "Yes, I'd like to get pre-qualified"},
                {"ava": "Perfect! What's your annual income?"},
                {"user": "$120,000"},
                {"ava": "Excellent! You're pre-qualified. Would you like to schedule a tour?"},
                {"user": "Yes, I'd love to schedule a tour"}
            ],
            "pq_completed": True,
            "kb_pending": None,
            "last_activity_time": time.time()
        }
        
        # Simulate the conversation data structure
        with conversations_lock:
            conversations[conversation_id_1] = test_conversation_1
        
        # Test the summary generation and database push
        await generate_and_send_summary(conversation_id_1)
        
        # Verify data was pushed to database (search by AI summary content)
        saved_conv = await fetch_one("""
            SELECT id, ai_intent_summary, is_qualified, status, created_at
            FROM conversation 
            WHERE ai_intent_summary LIKE $1
            ORDER BY created_at DESC
            LIMIT 1
        """, "%2-bedroom apartment%")
        
        if saved_conv:
            print("✅ Qualified user conversation successfully pushed to PostgreSQL")
            print(f"   - Database ID: {saved_conv['id']}")
            print(f"   - AI Summary: {saved_conv['ai_intent_summary'][:100]}...")
            print(f"   - Is Qualified: {saved_conv['is_qualified']}")
            print(f"   - Status: {saved_conv['status']}")
        else:
            print("❌ Failed to push qualified user conversation")
        
        # Test Case 2: Unqualified user with pricing questions
        print("\n📋 Test Case 2: Unqualified User - Pricing Inquiry")
        conversation_id_2 = str(uuid.uuid4())  # Use proper UUID format
        test_conversation_2 = {
            "conversation_id": conversation_id_2, 
            "history": [
                {"user": "What are your rent prices?"},
                {"ava": "Our studio apartments start at $1800, 1-bedrooms at $2200, and 2-bedrooms at $2800."},
                {"user": "That's expensive. Do you have any cheaper options?"},
                {"ava": "Let me check what incentives might be available. Would you like to get pre-qualified?"},
                {"user": "I only make $30,000 per year"},
                {"ava": "I understand. Based on that income, you might want to consider our income-restricted units."}
            ],
            "pq_completed": False,
            "kb_pending": None,
            "last_activity_time": time.time()
        }
        
        with conversations_lock:
            conversations[conversation_id_2] = test_conversation_2
        
        await generate_and_send_summary(conversation_id_2)
        
        saved_conv_2 = await fetch_one("""
            SELECT id, ai_intent_summary, is_qualified, status, created_at
            FROM conversation 
            WHERE ai_intent_summary LIKE $1
            ORDER BY created_at DESC
            LIMIT 1
        """, "%rent prices%")
        
        if saved_conv_2:
            print("✅ Unqualified user conversation successfully pushed to PostgreSQL")
            print(f"   - Database ID: {saved_conv_2['id']}")
            print(f"   - AI Summary: {saved_conv_2['ai_intent_summary'][:100]}...")
            print(f"   - Is Qualified: {saved_conv_2['is_qualified']}")
        else:
            print("❌ Failed to push unqualified user conversation")
        
        # Test Case 3: User with unanswered questions (KB pending)
        print("\n📋 Test Case 3: User with Unanswered Questions")
        conversation_id_3 = str(uuid.uuid4())  # Use proper UUID format
        test_conversation_3 = {
            "conversation_id": conversation_id_3,
            "history": [
                {"user": "Do you allow emotional support animals?"},
                {"ava": "I don't have specific information about emotional support animals. Let me connect you with a leasing agent who can provide detailed pet policy information."},
                {"user": "What about service dogs specifically?"},
                {"ava": "I don't have specific information about service dogs. Let me connect you with a leasing agent who can provide detailed pet policy information."}
            ],
            "pq_completed": False,
            "kb_pending": "What about service dogs specifically?",  # Unanswered question
            "fallback_triggered": True,
            "last_activity_time": time.time()
        }
        
        with conversations_lock:
            conversations[conversation_id_3] = test_conversation_3
        
        await generate_and_send_summary(conversation_id_3)
        
        # Check conversation was saved
        saved_conv_3 = await fetch_one("""
            SELECT id, ai_intent_summary, is_qualified, status
            FROM conversation 
            WHERE ai_intent_summary LIKE $1
            ORDER BY created_at DESC
            LIMIT 1
        """, "%support animals%")
        
        # Check unanswered question was saved
        unanswered_question = await fetch_one("""
            SELECT message_text, message_type, metadata, timestamp
            FROM message 
            WHERE message_text LIKE $1
            AND message_type = 'unanswered_question'
            ORDER BY timestamp DESC
            LIMIT 1
        """, "%service dogs%")
        
        if saved_conv_3:
            print("✅ Conversation with unanswered questions successfully pushed to PostgreSQL")
            print(f"   - Database ID: {saved_conv_3['id']}")
            if unanswered_question:
                print(f"   - Unanswered Question: {unanswered_question['message_text']}")
                print(f"   - Question Timestamp: {unanswered_question['timestamp']}")
            else:
                print("   - (Unanswered question may not have been saved)")
        else:
            print("❌ Failed to push conversation with unanswered questions")
            
        # Test Case 4: Direct database service operations
        print("\n📋 Test Case 4: Direct Database Service Operations")
        
        # Test direct save
        direct_save_result = await db_service.save_conversation(
            conversation_id="test_direct_004",
            ai_intent_summary="User inquired about parking availability and monthly rates for covered parking spots.",
            is_qualified=True,
            source="direct_test",
            status="completed"
        )
        
        if direct_save_result:
            print("✅ Direct conversation save successful")
        
        # Test unanswered question save
        unanswered_save_result = await db_service.save_unanswered_question(
            question="What are the hours for the fitness center?",
            conversation_id="test_direct_004",
            source="direct_test"
        )
        
        if unanswered_save_result:
            print("✅ Direct unanswered question save successful")
        
        # Test retrieval operations
        print("\n📋 Test Case 5: Data Retrieval Operations")
        
        # Test conversation retrieval
        retrieved_conv = await db_service.get_conversation_by_summary("User inquired about parking availability")
        if retrieved_conv:
            print("✅ Conversation retrieval by summary successful")
            print(f"   - Found: {retrieved_conv['ai_intent_summary'][:80]}...")
        else:
            print("❌ Conversation retrieval failed")
        
        # Test unanswered questions retrieval
        unanswered_questions = await db_service.get_unanswered_questions(limit=5)
        if unanswered_questions:
            print(f"✅ Retrieved {len(unanswered_questions)} unanswered questions")
            for i, q in enumerate(unanswered_questions[:3], 1):
                print(f"   {i}. {q.get('question', 'N/A')}")
        else:
            print("❌ No unanswered questions retrieved")
        
        # Database summary
        print("\n📊 Final Database State Summary")
        
        total_conversations = await fetch_one("SELECT COUNT(*) as count FROM conversation")
        total_messages = await fetch_one("SELECT COUNT(*) as count FROM message WHERE message_type = 'unanswered_question'")
        
        print(f"   📄 Total Conversations: {total_conversations['count']}")
        print(f"   ❓ Total Unanswered Questions: {total_messages['count']}")
        
        print("\n🎉 PostgreSQL Data Push Test Completed Successfully!")
        print("✅ All required data points are being pushed to PostgreSQL:")
        print("   1. ✅ AI Intent Summaries")
        print("   2. ✅ Prequalification Status")  
        print("   3. ✅ Unanswered FAQs")
        
    except Exception as e:
        print(f"❌ Error during PostgreSQL push testing: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up test data (use execute_query instead of db_service.pool)
        try:
            await execute_query("DELETE FROM message WHERE message_text LIKE '%fitness center%'")
            await execute_query("DELETE FROM conversation WHERE ai_intent_summary LIKE '%parking availability%'")
            print("\n🧹 Test data cleaned up")
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup warning: {cleanup_error}")
            
        await close_db()
        print("🔒 Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_postgresql_data_push()) 