from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
import app  # We can import the logic from app.py
import uvicorn
import webbrowser
import threading

server = FastAPI()

# Allow frontend HTML to call this API
server.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"

class ChatRequestClear(BaseModel):
    session_id: str = "default"

class ChatResponse(BaseModel):
    response: str

@server.get("/")
async def serve_frontend():
    return FileResponse("index.html")

@server.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # Process through the original career_chatbot function in app.py
    ans = await app.acareer_chatbot(request.message, request.session_id)
    return ChatResponse(response=ans)

@server.post("/clear")
async def clear_chat(request: ChatRequestClear = None):
    # In case the frontend sends an empty body on clear
    session_id = request.session_id if request else "default"
    app.clear_memory(session_id)
    return {"status": "cleared"}

def open_browser():
    webbrowser.open("http://localhost:8000")

if __name__ == "__main__":
    # Ensure the browser only opens once by checking an environment variable Uvicorn sets
    import os
    if not os.getenv("PROMETHEUS_MULTIPROC_DIR") and not os.getenv("RUN_MAIN"):
        threading.Timer(1.5, open_browser).start()
    uvicorn.run("api:server", host="0.0.0.0", port=8000, reload=True)