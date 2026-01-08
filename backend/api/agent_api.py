from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional

from backend.ai_model.agent.agent_controller import AgentController

router = APIRouter()

agent = AgentController()


class ChatRequest(BaseModel):
    query: str
    session_id: str = "default_session"
    mode: str = "raw"  # Answer mode: raw, structured, exam, study, debug


@router.post("/chat/stream")
def chat_stream(req: ChatRequest):
    return StreamingResponse(
        agent.stream_query(req.session_id, req.query, "demo_user", mode=req.mode), 
        media_type="application/x-ndjson"
    )

@router.get("/documents")
def get_documents():
    """List all documents currently indexed."""
    try:
        docs = agent.retriever.retriever.get_unique_documents()
        return {"documents": docs, "count": len(docs)}
    except Exception as e:
        return {"error": str(e), "documents": []}

# --- Register Routers ---
# Note: In a real app, this would be in main.py, but for this structure we are importing here or expecting main.py to import this.
# Let's check where `app` is defined. It seems missing here, so I will just leave the router definition and ensure `run_rakshakosh.bat` points to the right entrypoint.
# Wait, looking at `api_server.py`, it imports `APIRouter`.
# I should probably update `api_server.py` to be the entrypoint or check if there is a `main.py`.
# Let's check directory first.
