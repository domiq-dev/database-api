# tools/faq_tool.py
"""
FAQ lookup tool for Ava.
• FAQ_TOOL: function schema for the LLM
• lookup_faq(query) -> str : real HTTP call to RAG endpoint
"""

import requests

FAQ_TOOL = {
    "type": "function",
    "function": {
        "name": "lookup_faq",
        "description": "Ask the RAGBOT FAQ API and return the answer.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The prospect's FAQ question"
                }
            },
            "required": ["query"]
        }
    }
}

_ENDPOINT = "http://3.16.255.36:8000/rag"

def lookup_faq(query: str) -> str:
    """Call RAG endpoint and return plain-text answer."""
    try:
        resp = requests.post(
            _ENDPOINT,
            json={"query": query},
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("answer", "Sorry, I couldn't find an answer.")
    except Exception as exc:
        return f"Sorry, there was an error fetching that answer ({exc})."
