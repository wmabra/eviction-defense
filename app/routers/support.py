"""Support contact form — sends messages to support@evictions.help."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from app.services.email_service import send_email
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/support", tags=["support"])


class ContactRequest(BaseModel):
    name: str
    email: str
    reason: str
    message: str


class SupportConfigResponse(BaseModel):
    phone: str


@router.post("/contact")
def submit_contact(req: ContactRequest):
    """Send a contact form submission to support@evictions.help."""
    subject = f"Support: {req.reason} — from {req.name}"
    body = f"""SUPPORT REQUEST — {req.reason}

From: {req.name}
Email: {req.email}

Message:
{req.message}

---
Submitted via evictions.help/support contact form.
"""

    ok = send_email(
        to="support@evictions.help",
        subject=subject,
        body=body,
    )

    if not ok:
        logger.info(f"Contact form submitted by {req.name} ({req.email}): {req.reason}")

    return {"status": "ok", "sent": ok}


@router.get("/config", response_model=SupportConfigResponse)
def support_config():
    """Return support configuration (phone number, etc.)."""
    from app.config import settings
    return SupportConfigResponse(
        phone=settings.support_phone or "Coming soon"
    )
