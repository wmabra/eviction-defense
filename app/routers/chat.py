"""Chat-based intake API endpoints."""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.chat import get_chat_response

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    case_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    ready_for_eligibility: bool = False
    extracted_data: dict | None = None


@router.post("/send", response_model=ChatResponse)
def send_message(req: ChatRequest):
    """Send a message to the AI intake specialist."""
    messages = [{"role": m.role, "content": m.content} for m in req.messages]
    result = get_chat_response(messages)
    return ChatResponse(**result)


@router.post("/reset")
def reset_chat():
    """Reset the chat session."""
    return {"status": "ok", "message": "Chat session reset."}
