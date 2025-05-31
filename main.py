import os
import json
import openai
import re
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import threading
import time
import requests
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime

# Load environment variables and initialize OpenAI client
load_dotenv()
client = openai.OpenAI()
MODEL = "gpt-4.1-2025-04-14"

# Import internal modules
import agents.helper as helper_agent
import agents.ava as ava_agent
from tools import faq_tool
from tools.preq_tool import begin_prequalification, complete_prequalification
from analytics import init_analytics, track

# Initialize FastAPI application
app = FastAPI(title="Ava Leasing Chatbot")
conversations: dict[str, dict] = {}
conversations_lock = threading.Lock()

# Define Pydantic models
class ChatRequest(BaseModel):
    conversation_id: str
    turn_id: int
    user_message: str
    end_signal: bool = False
    # Amplitude tracking fields
    user_id: str = None
    session_id: str = None
    device_id: str = None

class ChatResponse(BaseModel):
    reply: str
    data: dict
    variables: dict
    # New fields for complete API response
    is_qualified: bool = None
    ai_intent_summary: str = None
    fallback: bool = False
    kb_pending: str = None
    source: str = "LLM"

# Define all boolean variables
all_variables = [
    "Full_name", "Bedroom_size", "Calendar", "User_action", "Faq", "YES/NO",
    "Incentive", "Price_range", "Work_place", "Occupancy", "Pet", "Features",
    "Tour", "Save_25", "Save_50"
]

# Define keyword-based triggers
specific_triggers = {
    "Full_name": ["Full Name"],
    "Bedroom_size": ["bedroom size"],
    "Calendar": ["move-in date"],
    "User_action": ["next action"],
    "Faq": ["top questions"],
    "Incentive": ["$ off", "save $"],
    "Price_range": ["price range"],
    "Work_place": ["work place"],
    "Occupancy": ["how many people (occupants)"],
    "Pet": ["(pets) with you"],
    "Features": ["special features"],
    "Tour": ["in-person tour", "self-guided tour", "virtual tour"],
    "Save_25": ["$25, save"],
    "Save_50": ["$50, save"]
}

yes_no_triggers = ["Is...?", "Are...?", "Can...?", "Could...?", "Will...?", "Would...?", "Shall...?", "Should...?", "May...?", "Might...?", "Have...?", "Has...?", "Had...?"]

# Fallback detection keywords and patterns
FALLBACK_PATTERNS = [
    r"i don't understand",
    r"i'm not sure",
    r"could you clarify",
    r"what do you mean",
    r"can you explain",
    r"i don't know",
    r"let me check with",
    r"i need to ask",
    r"that's beyond my",
    r"i cannot help with"
]

FALLBACK_RESPONSE = "We are connecting you to the manager now. Could you please enter your email address or phone number below? They will reach out ASAP."

def get_triggered_variable(response):
    response_lower = response.lower()
    for var, keywords in specific_triggers.items():
        if any(keyword.lower() in response_lower for keyword in keywords):
            return var
    for keyword in yes_no_triggers:
        if keyword.lower() in response_lower:
            return "YES/NO"
    return None

def detect_fallback(ai_response: str, confidence_score: float = None) -> bool:
    """Detect if AI response indicates a fallback scenario"""
    response_lower = ai_response.lower()
    
    # Check for low confidence score if provided
    if confidence_score is not None and confidence_score < 0.7:
        return True
    
    # Check for fallback patterns in response
    for pattern in FALLBACK_PATTERNS:
        if re.search(pattern, response_lower):
            return True
    
    # Check if response is too short or generic
    if len(ai_response.strip()) < 20:
        return True
    
    return False

def track_fallback(user_id: str, session_id: str, question: str, chat_history: list, device_id: str = None, conversation_id: str = None):
    """Track fallback event and KB gap"""
    try:
        # Track Fallback Triggered event
        props = {
            "session_id": session_id,
            "question_text": question,
            "chat_history_length": len(chat_history)
        }
        if conversation_id:
            props["conversation_id"] = conversation_id
            
        track(user_id, "fallback_triggered", props,
              device_id=device_id, session_id=session_id)
        
        # Track KB Gap Logged event
        kb_gap_props = {
            "session_id": session_id,
            "question_text": question,
            "chat_history": json.dumps(chat_history[-5:])  # Last 5 messages for context
        }
        if conversation_id:
            kb_gap_props["conversation_id"] = conversation_id
            
        track(user_id, "kb_gap_logged", kb_gap_props,
              device_id=device_id, session_id=session_id)
        
        print(f"Tracked fallback and KB gap for user {user_id}")
    except Exception as e:
        print(f"Error tracking fallback: {e}")

def generate_ai_intent_summary(history: list) -> str:
    """Generate AI intent summary - max 5 sentences"""
    if not history:
        return "No conversation history available."
    
    # Prepare conversation history for summary
    conversation_text = "\n".join([
        f"User: {turn.get('user', '')}\nAva: {turn.get('ava', '')}" 
        for turn in history if isinstance(turn, dict)
    ])
    
    prompt = f"""
    Generate a brief summary (maximum 5 sentences) of this conversation focusing on:
    1. User's main intent and needs
    2. Key information gathered (bedroom size, move-in date, etc.)
    3. Actions taken (toured, prequalified, etc.)
    4. Any special requests or concerns
    
    Conversation:
    {conversation_text}
    
    Summary:
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"Error generating AI intent summary: {e}")
        return "Summary generation failed."

SENTENCE_ENDINGS = re.compile(r'([.?!])')

# Function to generate and send AI summary
def generate_and_send_summary(conversation_id):
    try:
        # Get conversation data with minimal lock time
        with conversations_lock:
            if conversation_id not in conversations:
                return
            data = conversations[conversation_id].copy()  # Make a copy to work outside the lock
        
        history = data.get("history", [])
        if not history:
            # No history to summarize, just remove the conversation
            with conversations_lock:
                if conversation_id in conversations:
                    del conversations[conversation_id]
            return
            
        # Generate AI intent summary (5 sentences max)
        ai_intent_summary = generate_ai_intent_summary(history)
        
        prompt = f"""
        Please generate a summary based on the following conversation history and extract the following information:
        - Whether the user wanted to book a tour (Yes/No)
        - Whether the user is qualified (Yes/No)
        - What incentives the user accepted (list of incentive names)

        Conversation History:
        {json.dumps(history, ensure_ascii=False)}

        Return the result in JSON format with the following fields:
        {{
            "summary": "Conversation summary",
            "book_tour": "Yes/No",
            "qualified": "Yes/No",
            "incentives_accepted": ["incentive1", "incentive2", ...]
        }}
        """
        
        try:
            # Add timeout to prevent hanging
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                timeout=30  # 30 second timeout
            )
            summary_text = response.choices[0].message.content
            summary_data = json.loads(summary_text)
        except Exception as e:
            print(f"Error generating AI summary for conversation {conversation_id}: {e}")
            # Create a basic summary if AI fails
            summary_data = {
                "summary": "Conversation completed (AI summary failed)",
                "book_tour": "Unknown",
                "qualified": "Unknown", 
                "incentives_accepted": []
            }

        # Prepare structured API response
        api_response = {
            "conversation_id": conversation_id,
            "summary": summary_data["summary"],
            "book_tour": summary_data["book_tour"],
            "qualified": summary_data["qualified"],
            "incentives_accepted": summary_data["incentives_accepted"],
            "ai_intent_summary": ai_intent_summary,
            "is_qualified": summary_data["qualified"] == "Yes",
            "source": "LLM",
            "timestamp": datetime.now().isoformat(),
            # Include all conversation data
            "full_data": data
        }
        
        print("Structured API Response:")
        print(json.dumps(api_response, indent=2))
        
        # Store summary in conversation data and mark as generated
        with conversations_lock:
            if conversation_id in conversations:
                conversations[conversation_id]["final_summary"] = api_response
                conversations[conversation_id]["summary_generated"] = True
                conversations[conversation_id]["summary_generated_at"] = time.time()
                
    except Exception as e:
        print(f"Error in generate_and_send_summary for conversation {conversation_id}: {e}")
        # Remove problematic conversation
        with conversations_lock:
            if conversation_id in conversations:
                del conversations[conversation_id]

# Function to check inactive conversations
def check_inactive_conversations():
    try:
        current_time = time.time()
        inactive_conversations = []
        
        # Quickly identify inactive conversations with minimal lock time
        with conversations_lock:
            for conversation_id in list(conversations.keys()):
                conv_data = conversations[conversation_id]
                last_activity_time = conv_data.get("last_activity_time", 0)
                summary_generated = conv_data.get("summary_generated", False)
                summary_generated_at = conv_data.get("summary_generated_at", 0)
                
                # Check if conversation is inactive for 2 minutes
                if current_time - last_activity_time > 120:
                    # If no summary generated yet, or if activity resumed after summary and now inactive again
                    if not summary_generated or (summary_generated and last_activity_time > summary_generated_at):
                        inactive_conversations.append(conversation_id)
        
        # Process inactive conversations outside the lock
        for conversation_id in inactive_conversations:
            try:
                print(f"Generating summary for inactive conversation: {conversation_id}")
                generate_and_send_summary(conversation_id)
            except Exception as e:
                print(f"Error processing inactive conversation {conversation_id}: {e}")
                # Remove problematic conversation to prevent repeated errors
                with conversations_lock:
                    if conversation_id in conversations:
                        del conversations[conversation_id]
                        
    except Exception as e:
        print(f"Error in check_inactive_conversations: {e}")

# Startup and shutdown events for scheduler
@app.on_event("startup")
def startup_event():
    # Initialize Amplitude analytics
    init_analytics()
    print("Amplitude analytics initialized")
    
    scheduler = BackgroundScheduler()
    # Add job with max_instances=1 and replace_existing=True to prevent overlap
    scheduler.add_job(
        check_inactive_conversations, 
        IntervalTrigger(minutes=1),
        id='check_inactive_conversations',
        max_instances=1,
        replace_existing=True,
        coalesce=True  # Combine multiple pending executions into one
    )
    scheduler.start()
    app.scheduler = scheduler
    print("Background scheduler started")

@app.on_event("shutdown")
def shutdown_event():
    if hasattr(app, 'scheduler'):
        app.scheduler.shutdown(wait=False)  # Don't wait for jobs to complete
        print("Background scheduler stopped")

# Helper function to extract tracking info from request
def get_tracking_info(req: ChatRequest, request: Request = None):
    """Extract user tracking information from request"""
    user_id = req.user_id or req.conversation_id  # fallback to conversation_id
    session_id = req.session_id or req.conversation_id  # fallback to conversation_id
    device_id = req.device_id
    
    # Try to get from headers if not in request body
    if request:
        if not device_id:
            device_id = request.headers.get("x-device-id")
        if not req.session_id:
            session_id = request.headers.get("x-session-id") or session_id
            
    return user_id, session_id, device_id

# Function to track prequalification events
def track_prequalification_started(user_id: str, session_id: str, device_id: str = None, conversation_id: str = None):
    """Track when user starts prequalification process"""
    try:
        props = {"session_id": session_id}
        if conversation_id:
            props["conversation_id"] = conversation_id
            
        track(user_id, "prequalification_started", props,
              device_id=device_id, session_id=session_id)
        print(f"Tracked prequalification_started for user {user_id}")
    except Exception as e:
        print(f"Error tracking prequalification_started: {e}")

def track_prequalification_completed(user_id: str, session_id: str, passed: bool, device_id: str = None, conversation_id: str = None):
    """Track when prequalification process completes"""
    try:
        props = {
            "session_id": session_id,
            "passed": passed
        }
        if conversation_id:
            props["conversation_id"] = conversation_id
            
        track(user_id, "prequalification_completed", props,
              device_id=device_id, session_id=session_id)
        print(f"Tracked prequalification_completed for user {user_id}, passed: {passed}")
    except Exception as e:
        print(f"Error tracking prequalification_completed: {e}")

def track_chat_interaction(user_id: str, session_id: str, event_type: str, message: str = None, device_id: str = None, conversation_id: str = None):
    """Track general chat interactions"""
    try:
        props = {"session_id": session_id}
        if conversation_id:
            props["conversation_id"] = conversation_id
        if message:
            props["message_length"] = len(message)
            props["contains_question"] = "?" in message
            
        track(user_id, event_type, props,
              device_id=device_id, session_id=session_id)
        print(f"Tracked {event_type} for user {user_id}")
    except Exception as e:
        print(f"Error tracking {event_type}: {e}")

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, request: Request):
    # Extract tracking info
    user_id, session_id, device_id = get_tracking_info(req, request)
    
    with conversations_lock:
        data = conversations.setdefault(req.conversation_id, {})
        data["last_activity_time"] = time.time()
        # Reset summary_generated flag if there's new activity after a summary was generated
        if data.get("summary_generated", False) and data.get("summary_generated_at", 0) < data["last_activity_time"]:
            data["summary_generated"] = False
            
        data, done = helper_agent.process_turn(
            conversation_id=req.conversation_id,
            turn_id=req.turn_id,
            user_message=req.user_message,
            end_signal=req.end_signal,
            current_data=data,
        )
        if "history" not in data:
            data["history"] = []
        data["history"].append({"user": req.user_message})
        conversations[req.conversation_id] = data

    if done:
        variables = {var: False for var in all_variables}
        # Generate final summary when done
        ai_intent_summary = generate_ai_intent_summary(data.get("history", []))
        is_qualified = data.get("pq_completed", False)
        
        return ChatResponse(
            reply="", 
            data=data, 
            variables=variables,
            is_qualified=is_qualified,
            ai_intent_summary=ai_intent_summary,
            source="LLM"
        )

    is_faq = faq_tool.is_faq_question(req.user_message)
    print(f"FAQ detection result: {is_faq}")
    reply = ava_agent.process_turn(req.user_message, data, faq=is_faq)
    
    # Check for fallback
    is_fallback = detect_fallback(reply)
    kb_pending = None
    
    if is_fallback:
        # Track fallback event
        track_fallback(user_id, session_id, req.user_message, 
                      data.get("history", []), device_id, req.conversation_id)
        reply = FALLBACK_RESPONSE
        kb_pending = req.user_message  # Log the question that triggered fallback
    
    triggered_var = get_triggered_variable(reply)
    variables = {var: (var == triggered_var) for var in all_variables}

    with conversations_lock:
        data["history"][-1]["ava"] = reply
        if is_fallback:
            data["fallback_triggered"] = True
            data["kb_pending"] = kb_pending

    # Check if qualified
    is_qualified = data.get("pq_completed", False)
    
    return ChatResponse(
        reply=reply, 
        data=data, 
        variables=variables,
        is_qualified=is_qualified,
        fallback=is_fallback,
        kb_pending=kb_pending,
        source="LLM"
    )

# Streaming endpoint
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest, request: Request):
    # Extract tracking information
    user_id, session_id, device_id = get_tracking_info(req, request)
    
    # Track user message received event
    track_chat_interaction(user_id, session_id, "chat_message_received", 
                          req.user_message, device_id, req.conversation_id)
    
    # Check if user input triggers prequalification start
    if "get pre-qualified" in req.user_message.lower():
        begin_prequalification(user_id, session_id, device_id, req.conversation_id)
        print(f"Amplitude event triggered: prequalification_started for user {user_id}, session {session_id}")
    
    # Update conversation data
    with conversations_lock:
        data = conversations.setdefault(req.conversation_id, {})
        data["last_activity_time"] = time.time()
        # Reset summary_generated flag if there's new activity after a summary was generated
        if data.get("summary_generated", False) and data.get("summary_generated_at", 0) < data["last_activity_time"]:
            data["summary_generated"] = False
            
        data, done = helper_agent.process_turn(
            conversation_id=req.conversation_id,
            turn_id=req.turn_id,
            user_message=req.user_message,
            end_signal=req.end_signal,
            current_data=data,
        )
        if "history" not in data:
            data["history"] = []
        data["history"].append({"user": req.user_message})
        conversations[req.conversation_id] = data

    # If conversation ended
    if done:
        initial_variables = {var: False for var in all_variables}
        track_chat_interaction(user_id, session_id, "chat_session_ended", 
                              device_id=device_id, conversation_id=req.conversation_id)
        
        # Generate final summary
        ai_intent_summary = generate_ai_intent_summary(data.get("history", []))
        is_qualified = data.get("pq_completed", False)
        
        response_data = {
            "reply_chunk": "Session ended by signal.", 
            "data": data, 
            "variables": initial_variables, 
            "done": True,
            "is_qualified": is_qualified,
            "ai_intent_summary": ai_intent_summary,
            "source": "LLM"
        }
        
        return StreamingResponse(
            iter([json.dumps(response_data) + "\n"]),
            media_type="application/x-ndjson"
        )

    # Prepare messages for LLM
    messages_for_llm = [
        {"role": "system", "content": ava_agent.SYSTEM_INSTRUCTIONS},
        {"role": "system", "content": f"HELPER_DATA:\n{json.dumps(data)}"},
        {"role": "user", "content": req.user_message},
    ]

    # Check if it's an FAQ question
    is_faq = faq_tool.is_faq_question(req.user_message)
    print(f"FAQ detection result: {is_faq}")

    # Handle FAQ response
    if is_faq:
        reply_content = ava_agent.process_turn(req.user_message, data, faq=True)
        
        # Check for fallback
        is_fallback = detect_fallback(reply_content)
        kb_pending = None
        
        if is_fallback:
            # Track fallback event
            track_fallback(user_id, session_id, req.user_message, 
                          data.get("history", []), device_id, req.conversation_id)
            reply_content = FALLBACK_RESPONSE
            kb_pending = req.user_message
            
            with conversations_lock:
                data["fallback_triggered"] = True
                data["kb_pending"] = kb_pending
        
        triggered_var = get_triggered_variable(reply_content)
        current_variables = {var: (var == triggered_var) for var in all_variables}

        # Check if FAQ response triggers prequalification completion
        if "ve been pre-qualified" in reply_content.lower():
            complete_prequalification(user_id, session_id, passed=True, device_id=device_id, conversation_id=req.conversation_id)
            print(f"Amplitude event triggered: prequalification_completed for user {user_id}, session {session_id}, passed=True")

        track_chat_interaction(user_id, session_id, "faq_response_generated", 
                              reply_content, device_id, req.conversation_id)

        async def faq_response_generator():
            yield json.dumps({
                "variables": current_variables, 
                "data": data,
                "fallback": is_fallback,
                "kb_pending": kb_pending
            }) + "\n"
            yield json.dumps({"reply_chunk": reply_content}) + "\n"
            yield json.dumps({
                "completed_reply": reply_content, 
                "final_variables_update": current_variables,
                "is_qualified": data.get("pq_completed", False),
                "fallback": is_fallback,
                "kb_pending": kb_pending
            }) + "\n"

        return StreamingResponse(faq_response_generator(), media_type="application/x-ndjson")
    
    # Handle non-FAQ streaming response
    else:
        initial_variables = {var: False for var in all_variables}
        llm_stream = client.chat.completions.create(
            model=MODEL,
            messages=messages_for_llm,
            stream=True
        )

        async def sentence_by_sentence_generator():
            yield json.dumps({"variables": initial_variables, "data": data}) + "\n"
            sentence_buffer = ""
            full_response = ""
            is_fallback = False
            kb_pending = None
            
            for chunk in llm_stream:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    token = delta.content
                    sentence_buffer += token
                    full_response += token
                    parts = SENTENCE_ENDINGS.split(sentence_buffer)
                    idx = 0
                    while idx < len(parts) - 1:
                        current_sentence_part = parts[idx]
                        delimiter = parts[idx + 1]
                        if current_sentence_part or delimiter:
                            complete_sentence = current_sentence_part + delimiter
                            yield json.dumps({"reply_chunk": complete_sentence}) + "\n"
                        idx += 2
                    sentence_buffer = parts[-1] if parts else ""
            if sentence_buffer:
                yield json.dumps({"reply_chunk": sentence_buffer}) + "\n"
            
            # Check for fallback in complete response
            is_fallback = detect_fallback(full_response)
            if is_fallback:
                # Track fallback event
                track_fallback(user_id, session_id, req.user_message, 
                              data.get("history", []), device_id, req.conversation_id)
                full_response = FALLBACK_RESPONSE
                kb_pending = req.user_message
                
                with conversations_lock:
                    data["fallback_triggered"] = True
                    data["kb_pending"] = kb_pending
            
            # Check if system response triggers prequalification completion
            final_triggered_var = get_triggered_variable(full_response)
            final_variables = {var: (var == final_triggered_var) for var in all_variables}
            if "ve been pre-qualified" in full_response.lower():
                complete_prequalification(user_id, session_id, passed=True, device_id=device_id, conversation_id=req.conversation_id)
                print(f"Amplitude event triggered: prequalification_completed for user {user_id}, session {session_id}, passed=True")
                with conversations_lock:
                    data["pq_completed"] = True
            
            yield json.dumps({
                "completed_reply": full_response, 
                "final_variables_update": final_variables,
                "is_qualified": data.get("pq_completed", False),
                "fallback": is_fallback,
                "kb_pending": kb_pending
            }) + "\n"
            
            # Track streaming response completed event
            track_chat_interaction(user_id, session_id, "streaming_response_completed", 
                                  full_response, device_id, req.conversation_id)
            
            with conversations_lock:
                data["history"][-1]["ava"] = full_response

        return StreamingResponse(sentence_by_sentence_generator(), media_type="application/x-ndjson")

# Enhanced browser UI for proper streaming support
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>Ava Leasing Chatbot</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }
        .main-content {
            display: flex;
            height: 600px;
        }
        .chat-section {
            flex: 1;
            display: flex;
            flex-direction: column;
        }
        .variables-section {
            width: 300px;
            background: #f8f9fa;
            border-left: 1px solid #dee2e6;
            padding: 20px;
            overflow-y: auto;
        }
        #chat {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            border-bottom: 1px solid #eee;
        }
        .message {
            margin-bottom: 15px;
            padding: 10px 15px;
            border-radius: 18px;
            max-width: 80%;
            word-wrap: break-word;
        }
        .user-message {
            background: #007bff;
            color: white;
            margin-left: auto;
            text-align: right;
        }
        .ava-message {
            background: #e9ecef;
            color: #333;
            margin-right: auto;
        }
        .ava-streaming {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
        }
        .ava-fallback {
            background: #f8d7da;
            border: 1px solid #f5c6cb;
            color: #721c24;
        }
        .input-section {
            padding: 20px;
            background: white;
            border-top: 1px solid #eee;
        }
        .input-group {
            display: flex;
            gap: 10px;
        }
        #input {
            flex: 1;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 25px;
            outline: none;
            font-size: 14px;
        }
        #input:focus {
            border-color: #007bff;
        }
        #sendBtn {
            padding: 12px 24px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 25px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }
        #sendBtn:hover:not(:disabled) {
            background: #0056b3;
        }
        #sendBtn:disabled {
            background: #6c757d;
            cursor: not-allowed;
        }
        .variables-title {
            font-weight: bold;
            margin-bottom: 15px;
            color: #495057;
            border-bottom: 2px solid #007bff;
            padding-bottom: 5px;
        }
        .variable-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #e9ecef;
        }
        .variable-name {
            font-size: 12px;
            color: #6c757d;
        }
        .variable-status {
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: bold;
        }
        .variable-true {
            background: #d4edda;
            color: #155724;
        }
        .variable-false {
            background: #f8d7da;
            color: #721c24;
        }
        .loading {
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid #f3f3f3;
            border-top: 3px solid #007bff;
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }
        @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
        }
        .status-bar {
            padding: 10px 20px;
            background: #f8f9fa;
            border-top: 1px solid #dee2e6;
            font-size: 12px;
            color: #6c757d;
        }
        .debug-section {
            margin-top: 20px;
            padding: 10px;
            background: #f8f9fa;
            border: 1px solid #dee2e6;
            border-radius: 5px;
        }
        .debug-title {
            font-weight: bold;
            margin-bottom: 5px;
        }
        .debug-content {
            font-family: monospace;
            font-size: 11px;
            white-space: pre-wrap;
            max-height: 150px;
            overflow-y: auto;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h2>Ava Leasing Chatbot</h2>
            <p>Your intelligent apartment leasing assistant</p>
        </div>
        
        <div class="main-content">
            <div class="chat-section">
                <div id="chat"></div>
                <div class="input-section">
                    <div class="input-group">
                        <input id="input" placeholder="Type your message..." autofocus />
                        <button id="sendBtn" onclick="sendMessage()">Send</button>
                    </div>
                </div>
            </div>
            
            <div class="variables-section">
                <div class="variables-title">Conversation Variables</div>
                <div id="variables"></div>
                
                <div class="debug-section">
                    <div class="debug-title">Debug Info</div>
                    <div id="debug" class="debug-content"></div>
                </div>
            </div>
        </div>
        
        <div class="status-bar">
            <span id="status">Ready</span>
        </div>
    </div>

    <script>
        const conversationId = Date.now().toString();
        let turnId = 1;
        let isProcessing = false;
        let currentAvaMessageElement = null;
        let currentVariables = {};
        let debugInfo = {
            fallback: false,
            kb_pending: null,
            is_qualified: false,
            ai_intent_summary: null
        };

        // Generate tracking IDs
        const userId = `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const sessionId = `session_${Date.now()}`;
        const deviceId = `device_${navigator.userAgent.replace(/[^a-zA-Z0-9]/g, '').substr(0, 20)}_${Date.now()}`;

        console.log('Tracking IDs:', { userId, sessionId, deviceId });

        // Initialize variables display
        const allVariables = [
            "Full_name", "Bedroom_size", "Calendar", "User_action", "Faq", "YES/NO",
            "Incentive", "Price_range", "Work_place", "Occupancy", "Pet", "Features",
            "Tour", "Save_25", "Save_50"
        ];

        function initializeVariables() {
            allVariables.forEach(varName => {
                currentVariables[varName] = false;
            });
            updateVariablesDisplay();
        }

        function updateVariablesDisplay() {
            const variablesDiv = document.getElementById('variables');
            variablesDiv.innerHTML = '';
            
            Object.entries(currentVariables).forEach(([varName, value]) => {
                const item = document.createElement('div');
                item.className = 'variable-item';
                
                const nameSpan = document.createElement('span');
                nameSpan.className = 'variable-name';
                nameSpan.textContent = varName;
                
                const statusSpan = document.createElement('span');
                statusSpan.className = `variable-status variable-${value}`;
                statusSpan.textContent = value ? 'TRUE' : 'FALSE';
                
                item.appendChild(nameSpan);
                item.appendChild(statusSpan);
                variablesDiv.appendChild(item);
            });
        }

        function updateDebugInfo() {
            const debugDiv = document.getElementById('debug');
            debugDiv.textContent = JSON.stringify(debugInfo, null, 2);
        }

        function setStatus(message) {
            document.getElementById('status').textContent = message;
        }

        function addUserMessage(message) {
            const chatDiv = document.getElementById('chat');
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message user-message';
            messageDiv.textContent = `You: ${message}`;
            chatDiv.appendChild(messageDiv);
            chatDiv.scrollTop = chatDiv.scrollHeight;
        }

        function createAvaMessage(isFallback = false) {
            const chatDiv = document.getElementById('chat');
            const messageDiv = document.createElement('div');
            messageDiv.className = isFallback ? 'message ava-message ava-fallback' : 'message ava-message ava-streaming';
            messageDiv.innerHTML = 'Ava: <span class="loading"></span>';
            chatDiv.appendChild(messageDiv);
            chatDiv.scrollTop = chatDiv.scrollHeight;
            return messageDiv;
        }

        function updateAvaMessage(element, content, isComplete = false, isFallback = false) {
            if (isComplete) {
                element.className = isFallback ? 'message ava-message ava-fallback' : 'message ava-message';
                element.textContent = `Ava: ${content}`;
            } else {
                element.className = 'message ava-message ava-streaming';
                element.textContent = `Ava: ${content}`;
            }
            document.getElementById('chat').scrollTop = document.getElementById('chat').scrollHeight;
        }

        async function sendMessage() {
            const input = document.getElementById('input');
            const sendBtn = document.getElementById('sendBtn');
            const message = input.value.trim();
            
            if (!message || isProcessing) return;
            
            // Update UI state
            isProcessing = true;
            sendBtn.disabled = true;
            input.value = '';
            setStatus('Sending message...');
            
            // Add user message to chat
            addUserMessage(message);
            
            // Create Ava message element for streaming
            currentAvaMessageElement = createAvaMessage();
            
            try {
                const response = await fetch('/chat/stream', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'x-device-id': deviceId,
                        'x-session-id': sessionId,
                    },
                    body: JSON.stringify({
                        conversation_id: conversationId,
                        turn_id: turnId++,
                        user_message: message,
                        end_signal: false,
                        user_id: userId,
                        session_id: sessionId,
                        device_id: deviceId
                    })
                });

                if (!response.body) {
                    throw new Error('ReadableStream not supported');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let fullResponse = '';
                let isFallback = false;
                
                setStatus('Receiving response...');

                while (true) {
                    const { done, value } = await reader.read();
                    
                    if (done) break;
                    
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.trim()) {
                            try {
                                const data = JSON.parse(line);
                                
                                // Handle different types of streaming data
                                if (data.variables) {
                                    // Update variables display
                                    Object.assign(currentVariables, data.variables);
                                    updateVariablesDisplay();
                                }
                                
                                if (data.fallback !== undefined) {
                                    isFallback = data.fallback;
                                    debugInfo.fallback = data.fallback;
                                }
                                
                                if (data.kb_pending !== undefined) {
                                    debugInfo.kb_pending = data.kb_pending;
                                }
                                
                                if (data.is_qualified !== undefined) {
                                    debugInfo.is_qualified = data.is_qualified;
                                }
                                
                                if (data.ai_intent_summary !== undefined) {
                                    debugInfo.ai_intent_summary = data.ai_intent_summary;
                                }
                                
                                updateDebugInfo();
                                
                                if (data.reply_chunk) {
                                    // Append to the current response
                                    fullResponse += data.reply_chunk;
                                    updateAvaMessage(currentAvaMessageElement, fullResponse, false, isFallback);
                                }
                                
                                if (data.completed_reply) {
                                    // Final response received
                                    fullResponse = data.completed_reply;
                                    updateAvaMessage(currentAvaMessageElement, fullResponse, true, isFallback);
                                }
                                
                                if (data.final_variables_update) {
                                    // Final variables update
                                    Object.assign(currentVariables, data.final_variables_update);
                                    updateVariablesDisplay();
                                }
                                
                                if (data.done) {
                                    // Session ended
                                    setStatus('Session ended');
                                    return;
                                }
                                
                            } catch (e) {
                                console.error('Error parsing JSON:', e, 'Line:', line);
                            }
                        }
                    }
                }
                
                // Handle any remaining buffer
                if (buffer.trim()) {
                    try {
                        const data = JSON.parse(buffer);
                        if (data.completed_reply) {
                            updateAvaMessage(currentAvaMessageElement, data.completed_reply, true, isFallback);
                        }
                        if (data.final_variables_update) {
                            Object.assign(currentVariables, data.final_variables_update);
                            updateVariablesDisplay();
                        }
                        if (data.is_qualified !== undefined) {
                            debugInfo.is_qualified = data.is_qualified;
                        }
                        if (data.fallback !== undefined) {
                            debugInfo.fallback = data.fallback;
                        }
                        if (data.kb_pending !== undefined) {
                            debugInfo.kb_pending = data.kb_pending;
                        }
                        updateDebugInfo();
                    } catch (e) {
                        console.error('Error parsing final buffer:', e);
                    }
                }
                
                setStatus('Ready');
                
            } catch (error) {
                console.error('Error:', error);
                if (currentAvaMessageElement) {
                    updateAvaMessage(currentAvaMessageElement, 'Sorry, there was an error processing your message.', true);
                }
                setStatus('Error occurred');
            } finally {
                isProcessing = false;
                sendBtn.disabled = false;
                input.focus();
            }
        }

        // Event listeners
        document.getElementById('input').addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });

        // Initialize the application
        window.onload = function() {
            initializeVariables();
            updateDebugInfo();
            setStatus('Ready - Type a message to start chatting with Ava');
            document.getElementById('input').focus();
        };
    </script>
</body>
</html>
"""

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8001)), reload=True)