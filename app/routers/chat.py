"""Chat-based intake API endpoints."""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import ChatLog
from app.services.chat import get_chat_response, get_session, reset_session

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    case_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    ready_for_intake: bool = False
    extracted_data: dict | None = None


@router.post("/send", response_model=ChatResponse)
def send_message(req: ChatRequest, db: Session = Depends(get_db)):
    """Send a message to the AI intake specialist."""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    
    # Log the last user message to the database for review
    if req.case_id and messages:
        last_msg = messages[-1]
        try:
            log = ChatLog(case_id=req.case_id, role=last_msg["role"], content=last_msg["content"])
            db.add(log)
            db.commit()
        except Exception:
            pass
    
    result = get_chat_response(messages, case_id=req.case_id)
    
    # Log the AI response too
    if req.case_id and result.get("message"):
        try:
            log = ChatLog(case_id=req.case_id, role="assistant", content=result["message"])
            db.add(log)
            db.commit()
        except Exception:
            pass
    
    return ChatResponse(**result)


@router.get("/session/{case_id}")
def get_chat_session(case_id: str):
    """Get the current chat session data."""
    session = get_session(case_id)
    if not session:
        return {"case_id": case_id, "status": "no_session"}
    return {"case_id": case_id, **session}


@router.post("/reset")
def reset_chat(case_id: str | None = None):
    """Reset the chat session."""
    if case_id:
        reset_session(case_id)
    return {"status": "ok", "message": "Chat session reset."}
