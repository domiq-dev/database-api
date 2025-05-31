# agents/helper.py
"""
Helper-agent:
• Extracts / validates slots every turn
• Calls write_lead_record() when done
• Returns (updated_data, done_flag)
"""

import json, os, re
import openai
from tools.db_tool import WRITE_LEAD_TOOL, write_lead_record

# ── OpenAI v1 client + model name ──────────────────────────────────────────
client = openai.OpenAI()          # reads OPENAI_API_KEY from env
MODEL  = "gpt-4.1-2025-04-14"                # change if you use another model

# ── Your ORIGINAL long prompt goes here ───────────────────────────────────
SYSTEM_INSTRUCTIONS = """
    ----------------------------------------------------------------------
    0. PURPOSE
    ----------------------------------------------------------------------
    You run in the background during every chat session with the prospect.
    Your sole job is to:
      1. Extract and store structured data items from the prospect's
         messages.
      2. Immediately output **only** the data that has been collected so far,
         nothing else.
      3. When either (a) the prospect explicitly ends the conversation,
         or (b) all required data items are present, persist the record to
         PostgreSQL and stop emitting further output.
      4. Check very thoroughly that the data that is being given is all noted in the output.

    ----------------------------------------------------------------------
    1. DATA MODEL (TARGET TABLE `public.leads`)
    ----------------------------------------------------------------------
      conversation_id    UUID   PRIMARY KEY
      prospect_name      TEXT
      desired_bedrooms   SMALLINT
      move_in_date       DATE
      reason_for_move    TEXT
      employer           TEXT
      price_low          INT
      price_high         INT
      num_occupants      SMALLINT
      pets               JSONB      -- array of {{name,type,weight_lbs}}
      desired_features   TEXT[]
      pq_completed       BOOLEAN
      tour_type          TEXT
      tour_slot          TIMESTAMPTZ
      contact_email      TEXT
      contact_phone      TEXT
      created_at         TIMESTAMPTZ DEFAULT now()

    ----------------------------------------------------------------------
    2. INPUT FORMAT
    ----------------------------------------------------------------------
    Each turn you receive:

      {{
        "conversation_id" : "UUID",
        "turn_id"         : int,
        "user_message"    : str,    # raw prospect text
        "end_signal"      : bool,   # true if orchestrator signals convo end
        "current_data"    : {{      # latest key→value dict (may be empty)
            ...
        }}
      }}

    `current_data` is passed by reference; mutate it in‑place with any new
    validated fields you infer from the user_message.

    ----------------------------------------------------------------------
    3. EXTRACTION & VALIDATION
    ----------------------------------------------------------------------
      • Apply simple pattern matching + LLM reasoning to detect slot values.
      • Accept a value only if it passes the rules:

        Field               Validation
        ------------------- ----------------------------------------------
        prospect_name       letters/spaces, ≤40 chars
        desired_bedrooms    1, 2, or 3
        move_in_date        ISO date within today … +365 days
        price_low/high      500 ≤ value ≤ 10,000 and low ≤ high
        email               basic regex [^@]+@[^@]+\.[^@]+
        phone               E.164 or 10‑digit US pattern

    ----------------------------------------------------------------------
    4. OUTPUT FORMAT (EVERY TURN)
    ----------------------------------------------------------------------
    You MUST output a single, valid JSON object containing ONLY the key–value pairs
    you have collected so far (including those from prior turns). The JSON must be
    properly formatted with no additional text, comments, or markdown.

    Example of valid output:
    {"prospect_name": "Sam", "desired_bedrooms": 2, "move_in_date": "2025-08-15"}

    Invalid outputs (DO NOT DO THESE):
    ❌ "Here's the data: {"prospect_name": "Sam"}"
    ❌ ```json\n{"prospect_name": "Sam"}\n```
    ❌ {"prospect_name": "Sam"} and that's all I have so far

    If no new data were captured on the current turn, repeat the previously
    known data (idempotent output).

    ----------------------------------------------------------------------
    5. PERSISTENCE RULE
    ----------------------------------------------------------------------
    Required fields for completion:

      ["prospect_name","desired_bedrooms","move_in_date",
       "reason_for_move","price_low","price_high",
       "num_occupants","pq_completed","tour_slot",
       "contact_email","contact_phone"]

    Trigger `write_lead_record(record: dict)` **once** when:
      • `end_signal` == true OR
      • every required field is non‑null.

    After persistence, cease output.

    ----------------------------------------------------------------------
    6. FUNCTION SIGNATURE
    ----------------------------------------------------------------------
      write_lead_record(record: dict) -> None

    IMPORTANT: When calling this function, you must pass the data directly as the record parameter,
    not nested inside another object. For example:
    
    CORRECT: write_lead_record({"prospect_name": "John", "desired_bedrooms": 2, ...})
    INCORRECT: write_lead_record({"record": {"prospect_name": "John", ...}})

    ----------------------------------------------------------------------
    7. PROHIBITIONS
    ----------------------------------------------------------------------
      • Do **not** output guidance, comments, or analysis.
      • Do **not** reveal validation rules or internal logic.
      • Output must always be valid JSON without surrounding markdown.
      • No personally identifiable information beyond defined fields.


"""

# ── Utility to pull first {...} JSON object from any blob ──────────────────
_JSON_RE = re.compile(r"\{[\s\S]*?\}")

def _safe_load_json(blob: str) -> dict:
    m = _JSON_RE.search(blob or "")
    if not m:
        return {}
    try:
        return json.loads(m.group())
    except json.JSONDecodeError:
        return {}

# ── Public API used by main.py ─────────────────────────────────────────────
def process_turn(conversation_id: str,
                 turn_id: int,
                 user_message: str,
                 end_signal: bool,
                 current_data: dict):
    """
    • Sends one turn to the LLM
    • Mutates/merges current_data in-place
    • Returns (current_data, done_flag)
    """
    messages = [
        {"role": "system", "content": SYSTEM_INSTRUCTIONS},
        {"role": "user",   "content": json.dumps({
            "conversation_id": conversation_id,
            "turn_id": turn_id,
            "user_message": user_message,
            "end_signal": end_signal,
            "current_data": current_data
        })}
    ]

    try:
        rsp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=[WRITE_LEAD_TOOL],
            tool_choice="auto"
        )
        msg = rsp.choices[0].message
    except Exception as e:
        print(f"Error calling OpenAI API in helper: {e}")
        return current_data, False

    # ── CASE A: the model called write_lead_record() ───────────────────────
    if msg.tool_calls:
        for call in msg.tool_calls:
            if call.function.name == "write_lead_record":
                try:
                    args = json.loads(call.function.arguments)
                    print(f"Tool call arguments: {args}")  # Debug logging
                    
                    # Handle different possible argument structures
                    if "record" in args:
                        # If the LLM wrapped it in a "record" key
                        record_data = args["record"]
                    elif isinstance(args, dict) and len(args) > 0:
                        # If the LLM passed the data directly
                        # Check if it looks like lead data (has expected fields)
                        expected_fields = ["prospect_name", "desired_bedrooms", "move_in_date"]
                        if any(field in args for field in expected_fields):
                            record_data = args
                        else:
                            # If it's wrapped in another way, try to find the actual data
                            # Look for the first dict value that contains lead fields
                            record_data = None
                            for key, value in args.items():
                                if isinstance(value, dict) and any(field in value for field in expected_fields):
                                    record_data = value
                                    break
                            
                            if record_data is None:
                                print(f"Warning: Could not find valid lead data in tool call arguments: {args}")
                                continue
                    else:
                        print(f"Warning: Unexpected tool call arguments structure: {args}")
                        continue
                    
                    # Call the write function with the extracted data
                    write_lead_record(record_data)
                    current_data.update(record_data)   # keep cache fresh
                    return current_data, True          # done
                    
                except json.JSONDecodeError as e:
                    print(f"Error parsing tool call arguments: {e}")
                    print(f"Raw arguments: {call.function.arguments}")
                except KeyError as e:
                    print(f"KeyError in tool call: {e}")
                    print(f"Arguments structure: {args}")
                except Exception as e:
                    print(f"Unexpected error processing tool call: {e}")
                    print(f"Call details: {call}")
        # if some other unexpected tool, ignore and fall through

    # ── CASE B: the model emitted JSON as text ─────────────────────────────
    if msg.content:
        # Otherwise, parse the JSON object it emits
        try:
            # Try to parse the content as JSON
            updated = json.loads(msg.content)
        except json.JSONDecodeError:
            # If parsing fails, try to extract JSON from the text
            import re
            json_match = re.search(r'\{[^{}]*\}', msg.content)
            if json_match:
                try:
                    updated = json.loads(json_match.group())
                except json.JSONDecodeError:
                    # If still can't parse, return current data unchanged
                    return current_data, False
            else:
                # If no JSON found, return current data unchanged
                return current_data, False

        current_data.update(updated)
        return current_data, False