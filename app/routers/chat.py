"""Chat-based intake API endpoints."""
from fastapi import APIRouter, Depends
from typing import Any, cast
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import Case, ChatLog
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
    phase: int | None = None


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

    # Persist the extracted session state so a returning customer resumes
    # cleanly even after a server restart.
    if req.case_id and result.get("extracted_data"):
        try:
            case = db.query(Case).filter(Case.id == req.case_id).first()
            if case:
                case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright
                case.chat_session = {
                    "phase": "complete" if result.get("ready_for_intake") else "in_progress",
                    "collected_data": result["extracted_data"],
                }
                db.commit()
        except Exception:
            pass

    # Update the customer's progress bar from the completed intake phase
    # (25% at the start of intake → 55% once all 7 phases are done).
    if req.case_id and result.get("phase"):
        try:
            case = db.query(Case).filter(Case.id == req.case_id).first()
            if case:
                case = cast(Any, case)
                case.progress = 25 + round(min(7, int(result["phase"])) / 7 * 30)
                db.commit()
        except (TypeError, ValueError):
            pass

    return ChatResponse(**result)


@router.get("/session/{case_id}")
def get_chat_session(case_id: str, db: Session = Depends(get_db)):
    """Get the current chat session data (persisted, falls back to in-memory)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    persisted = cast(Any, case).chat_session if case is not None else None
    session = persisted if persisted else get_session(case_id)
    if not session:
        return {"case_id": case_id, "status": "no_session"}
    return {"case_id": case_id, **cast(dict, session)}


@router.post("/reset")
def reset_chat(case_id: str | None = None):
    """Reset the chat session."""
    if case_id:
        reset_session(case_id)
    return {"status": "ok", "message": "Chat session reset."}


@router.get("/history/{case_id}")
def get_chat_history(case_id: str, db: Session = Depends(get_db)):
    """Return the persisted chat history for a case, so a returning customer
    can pick up the conversation where they left off."""
    msgs = db.scalars(
        select(ChatLog)
        .where(ChatLog.case_id == case_id)
        .order_by(ChatLog.created_at.asc())
    ).all()
    return {
        "case_id": case_id,
        "messages": [{"role": m.role, "content": m.content} for m in msgs],
    }
