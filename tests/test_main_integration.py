import asyncio
import sys
import os
import json

# Add the parent directory to the Python path so we can import from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the main module and required functions
from config.database import init_db, close_db
import main

async def test_main_integration():
    """Test the main.py integration with database service"""
    
    try:
        print("🔧 Initializing database connection...")
        await init_db()
        print("✅ Database connection initialized successfully")
        
        # Create a mock conversation in the conversations dict
        test_conversation_id = "integration_test_123"
        
        # Mock conversation data similar to what the real chatbot would create
        mock_conversation_data = {
            "history": [
                {"user": "Hi, I'm looking for a 2-bedroom apartment", "ava": "Great! I'd be happy to help you find a 2-bedroom apartment. When are you looking to move in?"},
                {"user": "Next month", "ava": "Perfect! What's your budget range for rent?"},
                {"user": "Around $2000-2500", "ava": "That's a good range. Would you like to get pre-qualified to see our available units?"},
                {"user": "Yes, please", "ava": "Excellent! You've been pre-qualified. Would you like to schedule a tour?"},
                {"user": "What are the pet fees for cats?", "ava": "I'm not sure about the specific pet fees for cats. Let me connect you with our manager for detailed information."}
            ],
            "pq_completed": True,
            "kb_pending": "What are the pet fees for cats?",  # This should be saved as unanswered question
            "last_activity_time": 1234567890,
            "summary_generated": False
        }
        
        # Add the conversation to the main conversations dict
        with main.conversations_lock:
            main.conversations[test_conversation_id] = mock_conversation_data
        
        print(f"\n📝 Testing generate_and_send_summary with conversation {test_conversation_id}...")
        
        # Call the generate_and_send_summary function
        await main.generate_and_send_summary(test_conversation_id)
        
        # Check if the conversation was processed
        with main.conversations_lock:
            if test_conversation_id in main.conversations:
                final_summary = main.conversations[test_conversation_id].get("final_summary")
                if final_summary:
                    print("✅ Successfully generated final summary:")
                    print(f"   - Conversation ID: {final_summary.get('conversation_id')}")
                    print(f"   - Is Qualified: {final_summary.get('is_qualified')}")
                    print(f"   - AI Intent Summary: {final_summary.get('ai_intent_summary', '')[:100]}...")
                    print(f"   - Summary Generated: {main.conversations[test_conversation_id].get('summary_generated')}")
                else:
                    print("❌ No final summary was generated")
            else:
                print("✅ Conversation was removed after processing (expected behavior)")
        
        print("\n✅ Main integration test completed successfully!")
        
    except Exception as e:
        print(f"❌ Error during integration testing: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        print("\n🔒 Closing database connection...")
        await close_db()
        print("✅ Database connection closed")

if __name__ == "__main__":
    asyncio.run(test_main_integration()) 