# tools/preq_tool.py
from analytics import track

def begin_prequalification(user_id: str, session_id: str, device_id: str = None, conversation_id: str = None):
    props = {"session_id": session_id}
    if conversation_id:
        props["conversation_id"] = conversation_id
    track(user_id, "prequalification_started", props, device_id=device_id, session_id=session_id)

def complete_prequalification(user_id: str, session_id: str, passed: bool, device_id: str = None, conversation_id: str = None):
    props = {"session_id": session_id, "passed": passed}
    if conversation_id:
        props["conversation_id"] = conversation_id
    track(user_id, "prequalification_completed", props, device_id=device_id, session_id=session_id)