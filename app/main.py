from fastapi import FastAPI
from app.routers import conversation

app = FastAPI(title="Property Management Chatbot API")

# Only include the conversation router for the POC
app.include_router(conversation.router)

# You can add a root endpoint for API health check
@app.get("/")
async def root():
    return {"message": "Property Management Chatbot API", "version": "1.0.0"}