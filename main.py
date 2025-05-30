import os
import json
import openai # Ensure you have the openai package installed
import re
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv # Ensure you have python-dotenv installed

# Load environment variables and initialize OpenAI client
load_dotenv()  # Loads OPENAI_API_KEY, etc.
client = openai.OpenAI()
MODEL = "o4-mini"  # Restored to original model name

# Import internal modules
import agents.helper as helper_agent
import agents.ava    as ava_agent
import tools.simplified_faq_tool as faq_tool

# Initialize FastAPI application
app = FastAPI(title="Ava Leasing Chatbot")
conversations: dict[str, dict] = {}  # Stores conversation_id data dict

# Define Pydantic models
class ChatRequest(BaseModel):
    conversation_id: str
    turn_id: int
    user_message: str
    end_signal: bool = False

class ChatResponse(BaseModel):
    reply: str
    data: dict
    variables: dict  # Boolean variables field

# Define all boolean variables
all_variables = [
    "Full_name",
    "Bedroom_size",
    "Calendar",
    "User_action",
    "Faq",
    "YES/NO",
    "Incentive",
    "Price_range",
    "Work_place",
    "Occupancy",
    "Pet",
    "Features",
    "Tour",
    "Save_25",
    "Save_50"
]

# Define keyword-based triggers (Restored to original)
specific_triggers = {
    "Full_name": ["Full Name"],
    "Bedroom_size": ["bedroom size"],
    "Calendar": ["move-in date"],
    "User_action": ["next action"],
    "Faq": ["Ask Some Questions"],
    "Incentive": ["$ off", "save $"],
    "Price_range": ["price range"],
    "Work_place": ["work place"],
    "Occupancy": ["how many people (occupants)"],
    "Pet": [":(pets) with you"],
    "Features": ["special features"],
    "Tour": ["in-person tour", "self-guided tour", "virtual tour"],
    "Save_25": ["$25, save"],
    "Save_50": ["$50, save"]
}

# Restored to original
yes_no_triggers = ["Is...?", "Are...?", "Can...?", "Could...?", "Will...?", "Would...?", "Shall...?", "Should...?", "May...?", "Might...?", "Have...?", "Has...?", "Had...?"]

# Restored to original get_triggered_variable function
def get_triggered_variable(response):
    """Determine the triggered variable based on keyword matching in the response, prioritizing specific triggers over YES/NO"""
    response_lower = response.lower()
    # Check specific triggers first
    for var, keywords in specific_triggers.items():
        if any(keyword.lower() in response_lower for keyword in keywords):
            return var
    # Check YES/NO triggers only if no specific trigger is matched
    for keyword in yes_no_triggers:
        if keyword.lower() in response_lower: # Original logic for YES/NO
            return "YES/NO"
    return None

# Regex for sentence endings (Chinese and English punctuation).
# This is part of the streaming modification and its English comments are kept.
SENTENCE_ENDINGS = re.compile(r'([.?!])')

# Non-streaming endpoint (Restored to original logic for reply generation)
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # Process helper logic
    data = conversations.setdefault(req.conversation_id, {})
    data, done = helper_agent.process_turn(
        conversation_id=req.conversation_id,
        turn_id=req.turn_id,
        user_message=req.user_message,
        end_signal=req.end_signal,
        current_data=data,
    )
    conversations[req.conversation_id] = data
    if done:
        variables = {var: False for var in all_variables}
        return ChatResponse(reply="", data=data, variables=variables)

    # Check if the user message is an FAQ
    is_faq = faq_tool.is_faq_question(req.user_message)
    print(f"FAQ detection result: {is_faq}") # Original print statement

    # Generate Ava's reply with FAQ parameter (Restored to original logic)
    reply = ava_agent.process_turn(req.user_message, data, faq=is_faq)
    triggered_var = get_triggered_variable(reply)
    variables = {var: (var == triggered_var) for var in all_variables}
    return ChatResponse(reply=reply, data=data, variables=variables)

# Streaming endpoint (Contains the requested modifications for sentence-by-sentence streaming)
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    # Process helper logic
    data = conversations.setdefault(req.conversation_id, {})
    data, done = helper_agent.process_turn(
        conversation_id=req.conversation_id,
        turn_id=req.turn_id,
        user_message=req.user_message,
        end_signal=req.end_signal,
        current_data=data,
    )
    conversations[req.conversation_id] = data # Persist updated data

    # This 'if done' block's response format is part of the NDJSON streaming changes.
    if done:
        initial_variables = {var: False for var in all_variables}
        return StreamingResponse(
            iter([json.dumps({"reply_chunk": "Session ended by signal.", "data": data, "variables": initial_variables, "done": True}) + "\n"]),
            media_type="application/x-ndjson" # Consistent with overall streaming change
        )

    # Build messages for Ava (LLM)
    messages_for_llm = [
        {"role": "system", "content": ava_agent.SYSTEM_INSTRUCTIONS}, # Assuming SYSTEM_INSTRUCTIONS is an attribute of your ava_agent
        {"role": "system", "content": f"HELPER_DATA:\n{json.dumps(data)}"},
        {"role": "user", "content": req.user_message},
    ]

    # Check if the user message is an FAQ
    is_faq = faq_tool.is_faq_question(req.user_message)
    print(f"FAQ detection result: {is_faq}") # Original print statement

    if is_faq:
        # If it's an FAQ, get the (typically non-streamed) full answer.
        reply_content = ava_agent.process_turn(req.user_message, data, faq=True)
        triggered_var = get_triggered_variable(reply_content)
        current_variables = {var: (var == triggered_var) for var in all_variables}
        
        async def faq_response_generator():
            # FAQ response also follows the NDJSON streaming structure for client consistency.
            # First send metadata including variables, then send the reply content.
            yield json.dumps({"variables": current_variables, "data": data}) + "\n"
            yield json.dumps({"reply_chunk": reply_content}) + "\n"
            # Send a final completion message.
            yield json.dumps({"completed_reply": reply_content, "final_variables_update": current_variables}) + "\n"

        # Use application/x-ndjson for streaming multiple JSON objects.
        return StreamingResponse(faq_response_generator(), media_type="application/x-ndjson")
    else:
        # For non-FAQ cases, stream the response sentence by sentence from the LLM.
        # `variables` cannot be accurately calculated based on the full reply during initial streaming,
        # so an initial `False` state is sent.
        initial_variables = {var: False for var in all_variables}
        
        # Initiate stream from OpenAI
        llm_stream = client.chat.completions.create(
            model=MODEL,
            messages=messages_for_llm,
            stream=True
        )

        async def sentence_by_sentence_generator():
            # First, send a JSON object containing initial variables and current data.
            yield json.dumps({"variables": initial_variables, "data": data}) + "\n"
            
            sentence_buffer = ""
            full_response_for_final_variables = "" # Accumulates the full response.

            for chunk in llm_stream:
                delta = chunk.choices[0].delta
                if hasattr(delta, 'content') and delta.content is not None:
                    token = delta.content
                    sentence_buffer += token
                    full_response_for_final_variables += token

                    parts = SENTENCE_ENDINGS.split(sentence_buffer)
                    idx = 0
                    while idx < len(parts) - 1: 
                        current_sentence_part = parts[idx]
                        delimiter = parts[idx+1]
                        if current_sentence_part or delimiter:
                            complete_sentence = current_sentence_part + delimiter
                            yield json.dumps({"reply_chunk": complete_sentence}) + "\n"
                        idx += 2
                    sentence_buffer = parts[-1] if parts else ""

            if sentence_buffer:
                yield json.dumps({"reply_chunk": sentence_buffer}) + "\n"
            
            final_triggered_var = get_triggered_variable(full_response_for_final_variables)
            final_variables = {var: (var == final_triggered_var) for var in all_variables}
            
            yield json.dumps({"completed_reply": full_response_for_final_variables, "final_variables_update": final_variables}) + "\n"

        return StreamingResponse(sentence_by_sentence_generator(), media_type="application/x-ndjson")

# Development runner (Restored to original structure)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT", 8001)), reload=True)