# tools/simplified_faq_tool.py
"""
Simplified FAQ tool that uses LLM to determine if a question is FAQ-type
"""

import openai

client = openai.OpenAI()  # Use existing OpenAI client configuration
MODEL = "gpt-4o"  # Use the same model as the main application

FAQ_TOOL = {
    "type": "function",
    "function": {
        "name": "is_faq_question",
        "description": "Determine if the user's question is a frequently asked question (FAQ) type",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The user's question"
                }
            },
            "required": ["query"]
        }
    }
}

def is_faq_question(query: str) -> bool:
    """Determine if the question is an FAQ type"""
    print(f"Checking if question is FAQ type: '{query}'")
    
    # Use simple prompt engineering to let the LLM make the determination
    prompt = f"""
    Determine if the following user question is a frequently asked question (FAQ) about apartment leasing.
    Common questions typically involve: location, pricing, amenities, application process, policies, etc.
    Examples of FAQ questions:
    - What are the available units?
    - How much is the rent?
    - What amenities are included?
    - How many pets may I have?

    User question: "{query}"
    
    Please answer only with "true" or "false".
    """
    
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_completion_tokens=10     # Only need a short answer
        )
        
        answer = response.choices[0].message.content.strip().lower()
        result = "true" in answer  # Check if "true" is in the response
        print(f"LLM determination result: {answer} -> {result}")
        return result
    except Exception as e:
        print(f"LLM determination error: {e}")
        return False  # Default to False in case of error