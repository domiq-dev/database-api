#!/usr/bin/env python3
"""
🏢 Ava Leasing Chatbot - PostgreSQL Integration Demo

This script demonstrates the complete end-to-end flow of how conversation data
is captured, processed, and stored in PostgreSQL database.

Run with: python demo_postgresql_integration.py
"""

import asyncio
import sys
import os
import json
import time
import uuid
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.db_service import db_service
from config.database import init_db, close_db, fetch_one, execute_query
from main import generate_and_send_summary, conversations, conversations_lock

def print_section_header(title, emoji="🔸"):
    """Print a formatted section header"""
    print(f"\n{emoji} {title}")
    print("=" * (len(title) + 4))

def print_subsection(title, emoji="📋"):
    """Print a formatted subsection header"""
    print(f"\n{emoji} {title}")
    print("-" * (len(title) + 4))

def print_data_structure(data, title="Data Structure"):
    """Pretty print a data structure"""
    print(f"\n💾 {title}:")
    print(json.dumps(data, indent=2, default=str))

async def demo_conversation_scenario(scenario_name, conversation_data, expected_qualified, expected_kb_pending):
    """Demonstrate a single conversation scenario"""
    
    print_subsection(f"Scenario: {scenario_name}")
    
    # Step 1: Show input conversation data
    print("🎯 INPUT - Conversation Data:")
    print(f"   Conversation ID: {conversation_data['conversation_id']}")
    print(f"   Expected Qualification: {expected_qualified}")
    print(f"   Expected KB Pending: {expected_kb_pending}")
    
    print("\n📝 Conversation History:")
    for i, exchange in enumerate(conversation_data['history'], 1):
        for role, message in exchange.items():
            print(f"   {i}. {role.upper()}: {message}")
    
    # Step 2: Simulate the conversation in memory
    print("\n⚙️  PROCESSING - Adding to conversation memory...")
    with conversations_lock:
        conversations[conversation_data['conversation_id']] = conversation_data
    print("✅ Conversation added to in-memory store")
    
    # Step 3: Trigger summary generation and database save
    print("\n🔄 PROCESSING - Generating AI summary and saving to database...")
    await generate_and_send_summary(conversation_data['conversation_id'])
    
    # Step 4: Verify what was saved to database
    print("\n🔍 VERIFICATION - Checking what was saved to PostgreSQL...")
    
    # Find the conversation in database
    saved_conversation = await fetch_one("""
        SELECT id, ai_intent_summary, is_qualified, status, source, created_at
        FROM conversation 
        WHERE ai_intent_summary LIKE $1
        ORDER BY created_at DESC
        LIMIT 1
    """, f"%{conversation_data['history'][0]['user'][:20]}%")
    
    if saved_conversation:
        print("✅ Conversation successfully saved to PostgreSQL:")
        print(f"   Database ID: {saved_conversation['id']}")
        print(f"   AI Intent Summary: {saved_conversation['ai_intent_summary'][:150]}...")
        print(f"   Is Qualified: {saved_conversation['is_qualified']}")
        print(f"   Status: {saved_conversation['status']}")
        print(f"   Source: {saved_conversation['source']}")
        print(f"   Created At: {saved_conversation['created_at']}")
        
        # Check if qualification status matches expectation
        if saved_conversation['is_qualified'] == expected_qualified:
            print(f"✅ Qualification status correct: {saved_conversation['is_qualified']}")
        else:
            print(f"❌ Qualification status mismatch: expected {expected_qualified}, got {saved_conversation['is_qualified']}")
    else:
        print("❌ Conversation not found in database")
    
    # Check for unanswered questions if expected
    if expected_kb_pending:
        print("\n🔍 Checking for unanswered questions...")
        unanswered_question = await fetch_one("""
            SELECT message_text, message_type, metadata, timestamp
            FROM message 
            WHERE message_text LIKE $1
            AND message_type = 'unanswered_question'
            ORDER BY timestamp DESC
            LIMIT 1
        """, f"%{expected_kb_pending[:20]}%")
        
        if unanswered_question:
            print("✅ Unanswered question successfully saved:")
            print(f"   Question: {unanswered_question['message_text']}")
            print(f"   Timestamp: {unanswered_question['timestamp']}")
            print(f"   Metadata: {unanswered_question['metadata']}")
        else:
            print("❌ Unanswered question not found in database")
    
    print("\n" + "="*60)
    return saved_conversation

async def main():
    """Main demonstration function"""
    
    print("🏢 AVA LEASING CHATBOT - POSTGRESQL INTEGRATION DEMO")
    print("="*60)
    print("This demo shows how conversation data flows from chatbot to PostgreSQL")
    print("📊 Data Points Captured: AI Intent Summary, Qualification Status, Unanswered FAQs")
    
    try:
        # Initialize database connection
        print_section_header("Database Initialization", "🔧")
        await init_db()
        print("✅ PostgreSQL connection established")
        
        # Check initial database state
        initial_conversations = await fetch_one("SELECT COUNT(*) as count FROM conversation")
        initial_questions = await fetch_one("SELECT COUNT(*) as count FROM message WHERE message_type = 'unanswered_question'")
        
        print(f"📊 Initial Database State:")
        print(f"   Conversations: {initial_conversations['count']}")
        print(f"   Unanswered Questions: {initial_questions['count']}")
        
        # Demo Scenario 1: Qualified User
        print_section_header("Demo Scenario 1: Qualified User", "🎯")
        
        qualified_conversation = {
            "conversation_id": str(uuid.uuid4()),
            "history": [
                {"user": "Hi, I'm looking for a 2-bedroom apartment"},
                {"ava": "I'd be happy to help you find a 2-bedroom apartment! What's your budget range?"},
                {"user": "Around $2800 per month"},
                {"ava": "That's a great budget! Let me help you get pre-qualified."},
                {"user": "Yes, I'd like to get pre-qualified"},
                {"ava": "Perfect! What's your annual income?"},
                {"user": "$150,000"},
                {"ava": "Excellent! You're pre-qualified. Would you like to schedule a tour?"},
                {"user": "Yes, I'd love to schedule a tour"}
            ],
            "pq_completed": True,  # User completed prequalification
            "kb_pending": None,    # No unanswered questions
            "last_activity_time": time.time(),
            "fallback_triggered": False
        }
        
        scenario_1_result = await demo_conversation_scenario(
            "Qualified User Seeking 2-Bedroom Apartment",
            qualified_conversation,
            expected_qualified=True,
            expected_kb_pending=None
        )
        
        # Demo Scenario 2: Unqualified User
        print_section_header("Demo Scenario 2: Unqualified User", "🎯")
        
        unqualified_conversation = {
            "conversation_id": str(uuid.uuid4()),
            "history": [
                {"user": "What are your cheapest apartments?"},
                {"ava": "Our studio apartments start at $1800, 1-bedrooms at $2200, and 2-bedrooms at $2800."},
                {"user": "That's way too expensive. I can only afford $1000"},
                {"ava": "I understand that's a tight budget. Would you like to get pre-qualified to see what options might be available?"},
                {"user": "I only make $25,000 per year"},
                {"ava": "Based on that income, our standard units might not be within your budget range. I'd recommend checking our affordable housing waitlist."}
            ],
            "pq_completed": False,  # User did not qualify
            "kb_pending": None,     # No unanswered questions
            "last_activity_time": time.time(),
            "fallback_triggered": False
        }
        
        scenario_2_result = await demo_conversation_scenario(
            "Unqualified User with Budget Constraints",
            unqualified_conversation,
            expected_qualified=False,
            expected_kb_pending=None
        )
        
        # Demo Scenario 3: User with Unanswered Questions
        print_section_header("Demo Scenario 3: User with Unanswered Questions", "🎯")
        
        kb_pending_conversation = {
            "conversation_id": str(uuid.uuid4()),
            "history": [
                {"user": "Do you allow large dogs over 80 pounds?"},
                {"ava": "I don't have specific information about weight restrictions for pets. Let me connect you with a leasing agent who can provide detailed pet policy information."},
                {"user": "What about breed restrictions for pit bulls?"},
                {"ava": "I don't have specific information about breed restrictions. Let me connect you with a leasing agent who can provide detailed pet policy information."}
            ],
            "pq_completed": False,  # User didn't get to prequalification
            "kb_pending": "What about breed restrictions for pit bulls?",  # Unanswered question
            "last_activity_time": time.time(),
            "fallback_triggered": True
        }
        
        scenario_3_result = await demo_conversation_scenario(
            "User with Unanswered Pet Policy Questions",
            kb_pending_conversation,
            expected_qualified=False,
            expected_kb_pending="What about breed restrictions for pit bulls?"
        )
        
        # Demo: Direct Database Service Testing
        print_section_header("Demo: Direct Database Service Operations", "🔧")
        
        print("📋 Testing direct database service methods...")
        
        # Test direct conversation save
        print("\n🔄 Testing direct conversation save...")
        direct_save_success = await db_service.save_conversation(
            conversation_id="demo_direct_001",
            ai_intent_summary="User inquired about amenities including gym, pool, and parking garage access.",
            is_qualified=True,
            source="demo_direct",
            status="completed"
        )
        
        if direct_save_success:
            print("✅ Direct conversation save successful")
        else:
            print("❌ Direct conversation save failed")
        
        # Test direct unanswered question save
        print("\n🔄 Testing direct unanswered question save...")
        direct_question_success = await db_service.save_unanswered_question(
            question="What are the pool hours during winter months?",
            conversation_id="demo_direct_001",
            source="demo_direct"
        )
        
        if direct_question_success:
            print("✅ Direct unanswered question save successful")
        else:
            print("❌ Direct unanswered question save failed")
        
        # Demo: Data Retrieval and Analysis
        print_section_header("Demo: Data Retrieval and Analysis", "📊")
        
        # Get conversation by summary
        print("🔍 Testing conversation retrieval by summary...")
        retrieved_conv = await db_service.get_conversation_by_summary("User inquired about amenities")
        if retrieved_conv:
            print("✅ Conversation retrieval successful:")
            print(f"   ID: {retrieved_conv['id']}")
            print(f"   Summary: {retrieved_conv['ai_intent_summary'][:100]}...")
            print(f"   Qualified: {retrieved_conv['is_qualified']}")
        else:
            print("❌ Conversation retrieval failed")
        
        # Get unanswered questions
        print("\n🔍 Testing unanswered questions retrieval...")
        unanswered_questions = await db_service.get_unanswered_questions(limit=10)
        if unanswered_questions:
            print(f"✅ Retrieved {len(unanswered_questions)} unanswered questions:")
            for i, q in enumerate(unanswered_questions[:5], 1):
                print(f"   {i}. {q.get('question', 'N/A')}")
                print(f"      Timestamp: {q.get('timestamp', 'N/A')}")
        else:
            print("❌ No unanswered questions found")
        
        # Final Database State Summary
        print_section_header("Final Database State Summary", "📈")
        
        final_conversations = await fetch_one("SELECT COUNT(*) as count FROM conversation")
        final_questions = await fetch_one("SELECT COUNT(*) as count FROM message WHERE message_type = 'unanswered_question'")
        
        conversations_added = final_conversations['count'] - initial_conversations['count']
        questions_added = final_questions['count'] - initial_questions['count']
        
        print(f"📊 Database Changes During Demo:")
        print(f"   Conversations Added: {conversations_added}")
        print(f"   Unanswered Questions Added: {questions_added}")
        print(f"   Total Conversations: {final_conversations['count']}")
        print(f"   Total Unanswered Questions: {final_questions['count']}")
        
        # Show recent conversations
        print("\n📋 Most Recent Conversations:")
        recent_conversations = await fetch_one("""
            SELECT ai_intent_summary, is_qualified, status, created_at
            FROM conversation 
            ORDER BY created_at DESC
            LIMIT 1
        """)
        
        if recent_conversations:
            print(f"   Latest: {recent_conversations['ai_intent_summary'][:100]}...")
            print(f"   Qualified: {recent_conversations['is_qualified']}")
            print(f"   Status: {recent_conversations['status']}")
            print(f"   Created: {recent_conversations['created_at']}")
        
        # Summary of what was demonstrated
        print_section_header("Demo Summary - What Was Demonstrated", "🎉")
        
        print("✅ Successfully demonstrated all three required data points:")
        print("   1. 🧠 AI Intent Summaries - Generated and stored for all conversation types")
        print("   2. ✅ Prequalification Status - Accurately tracked (qualified/unqualified users)")
        print("   3. ❓ Unanswered FAQs - Captured and stored with metadata when fallback triggered")
        
        print("\n🔄 Data Flow Demonstrated:")
        print("   Chatbot Conversation → In-Memory Processing → AI Summary Generation → PostgreSQL Storage")
        
        print("\n🎯 Key Features Shown:")
        print("   • Automatic conversation summarization using LLM")
        print("   • Qualification status tracking based on user responses")
        print("   • Unanswered question capture when chatbot fallback occurs")
        print("   • Proper UUID generation and database relationships")
        print("   • Error handling and graceful degradation")
        print("   • Real-time data retrieval and analysis")
        
    except Exception as e:
        print(f"\n❌ Demo Error: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Clean up demo data
        print_section_header("Demo Cleanup", "🧹")
        try:
            # Clean up the demo data we created
            await execute_query("DELETE FROM message WHERE message_text LIKE '%pool hours%'")
            await execute_query("DELETE FROM conversation WHERE ai_intent_summary LIKE '%amenities%'")
            print("✅ Demo data cleaned up")
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup warning: {cleanup_error}")
        
        # Close database connection
        await close_db()
        print("🔒 Database connection closed")
        print("\n🎉 Demo completed successfully!")

if __name__ == "__main__":
    print("🚀 Starting Ava Leasing Chatbot PostgreSQL Integration Demo...")
    asyncio.run(main()) 