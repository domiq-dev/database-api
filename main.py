# main.py
import os, json, openai
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# ── ENV + OPENAI CLIENT ────────────────────────────────────────────────────
load_dotenv()                       # reads OPENAI_API_KEY, etc.
client = openai.OpenAI()
MODEL = "o4-mini"                   # switch if you use a different model

# ── INTERNAL MODULES ───────────────────────────────────────────────────────
import agents.helper as helper_agent
import agents.ava    as ava_agent
import tools.faq_tool as faq_tool   # FAQ_TOOL with {"type":"function",…}

# ── FASTAPI APP ────────────────────────────────────────────────────────────
app = FastAPI(title="Ava Leasing Chatbot")
conversations: dict[str, dict] = {}   # conversation_id → slot dict

# ── Pydantic models ────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    conversation_id: str
    turn_id: int
    user_message: str
    end_signal: bool = False

class ChatResponse(BaseModel):
    reply: str
    data: dict

# ── Non-streaming endpoint (optional) ──────────────────────────────────────
@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # helper step
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
        return ChatResponse(reply="", data=data)   # lead persisted – nothing to say

    # Ava step
    reply = ava_agent.process_turn(req.user_message, data)
    return ChatResponse(reply=reply, data=data)

# ── Streaming endpoint (preferred) ─────────────────────────────────────────
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    # helper step
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
        return StreamingResponse(iter([""]), media_type="text/plain")

    # build messages for Ava
    messages = [
        {"role": "system", "content": ava_agent.SYSTEM_INSTRUCTIONS},
        {"role": "system", "content": f"HELPER_DATA:\n{json.dumps(data)}"},
        {"role": "user",   "content": req.user_message},
    ]

    # stream reply
    stream = client.chat.completions.create(
        model   = MODEL,
        messages= messages,
        tools   = [faq_tool.FAQ_TOOL],
        tool_choice = "auto",
        stream  = True
    )

    def token_generator():
        for chunk in stream:
            delta = chunk.choices[0].delta
            if hasattr(delta, 'content') and delta.content is not None:
                yield delta.content

    return StreamingResponse(token_generator(), media_type="text/plain")

# ── Minimal browser UI for quick tests ─────────────────────────────────────
@app.get("/", response_class=HTMLResponse)
async def root():
    return """
<!DOCTYPE html><html><head><title>Ava Chat</title><style>
body{font-family:sans-serif;margin:2rem;}
#chat{border:1px solid #ccc;height:400px;overflow-y:scroll;padding:1rem;}
.user{color:blue}.ava{color:green}#input{width:80%}
</style></head><body>
<h2>Ava Leasing Chatbot</h2>
<div id="chat"></div>
<input id="input" placeholder="Type…" autofocus/>
<button onclick="sendMsg()">Send</button>
<script>
const id=Date.now().toString();let turn=1;
async function sendMsg(){
 const txt=document.getElementById('input').value.trim();
 if(!txt)return; append('You',txt,'user'); document.getElementById('input').value='';
 const res=await fetch('/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},
   body:JSON.stringify({conversation_id:id,turn_id:turn++,user_message:txt,end_signal:false})});
 const rd=res.body.getReader(),dec=new TextDecoder();let done=false,buf='';
 while(!done){const {value,done:d}=await rd.read();done=d;if(value){buf+=dec.decode(value);append('Ava',buf,'ava');}}
}
function append(who,msg,cls){const d=document.createElement('div');d.className=cls;d.textContent=`${who}: ${msg}`;
 document.getElementById('chat').appendChild(d);d.parentNode.scrollTop=1e9;}
window.onload=()=>sendMsg('');
</script></body></html>
"""

# ── Dev runner ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.getenv("PORT",8000)), reload=True)
