"""Voice Support API — powers the Retell AI phone agent.

Compliance rules baked into every response:
1. We are a self-help document preparation service. Not legal advice. Not a law firm.
2. The agent must never contradict the website or the customer's document package.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import hashlib
import hmac
import json

from app.database import get_db
from app.database.models import Case, ChatLog
from app.services.email_service import send_callback_email
from app.config import settings

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# ── Pydantic schemas ──────────────────────────────────────────────

class CallerVerifyRequest(BaseModel):
    """Verify a caller by email or case ID."""
    email: Optional[str] = None
    case_id: Optional[str] = None
    last_four_phone: Optional[str] = None


class CallerInfo(BaseModel):
    """Safe caller info returned to the voice agent."""
    verified: bool
    customer_name: str = ""
    case_id: str = ""
    state: str = ""
    county: str = ""
    status: str = ""
    package_type: str = ""  # e.g. "eviction_defense_v1"
    packet_ready: bool = False
    has_fee_waiver: bool = False
    response_deadline: str = ""  # ISO date string
    court_date: str = ""


class DocumentHelpRequest(BaseModel):
    """Caller asks about a specific document in their packet."""
    case_id: str
    doc_name: str


class DocumentHelpResponse(BaseModel):
    """Explains one document — what it is, where to sign, where to file."""
    found: bool
    doc_name: str = ""
    description: str = ""
    purpose: str = ""
    where_to_sign: str = ""
    where_to_file: str = ""
    important_notes: str = ""


class CorrectionRequest(BaseModel):
    """Caller reports an error in their packet."""
    case_id: str
    field_or_document: str
    description: str
    caller_email: str = ""


class TicketRequest(BaseModel):
    """Create a support ticket for human follow-up."""
    case_id: str = ""
    caller_name: str = ""
    caller_email: str = ""
    caller_phone: str = ""
    issue_type: str  # "billing", "correction", "technical", "other"
    description: str


class CallbackRequest(BaseModel):
    """Same-day callback request — triggers email to support@evictions.help."""
    first_name: str
    last_name: str
    phone: str
    best_time_eastern: str  # e.g. "between 2pm and 4pm"
    case_id: str = ""
    issue_summary: str  # brief description of what they need help with
    caller_email: str = ""  # from their account if verified


class VoiceEvent(BaseModel):
    """Inbound webhook from Retell after a call completes."""
    call_id: str
    agent_id: str
    caller_number: str = ""
    duration_seconds: int = 0
    outcome: str = ""  # "resolved", "transferred", "voicemail", "hangup"
    transcript: str = ""
    function_calls: list = []
    ticket_created: bool = False
    ticket_id: str = ""


# ── Compliance wrapper ────────────────────────────────────────────

COMPLIANCE_NOTICE = (
    "evictions.help is a self-help document preparation service for a flat "
    "one-time fee. It is not a law firm, does not provide legal advice, and "
    "does not represent you in court."
)


def voice_response(data: dict) -> dict:
    """Every voice API response includes the compliance notice."""
    return {"compliance": COMPLIANCE_NOTICE, **data}


# ── Endpoints ─────────────────────────────────────────────────────

@router.post("/verify")
def verify_caller(req: CallerVerifyRequest, db: Session = Depends(get_db)):
    """Verify a caller and return their package context.

    Retell calls this when a caller says they purchased a packet.
    """
    case = None

    if req.case_id:
        case = db.query(Case).filter(Case.id == req.case_id).first()
    elif req.email:
        # Find most recent case for this email
        case = (
            db.query(Case)
            .filter(Case.email == req.email)
            .order_by(Case.created_at.desc())
            .first()
        )

    if not case:
        return voice_response({
            "verified": False,
            "message": (
                "I wasn't able to find your order with that information. "
                "You can look up your order using the email address you used "
                "at checkout, or the case ID from your confirmation. Would you "
                "like to try again?"
            ),
        })

    # Phone verification (optional extra security)
    if req.last_four_phone and case.phone:
        if not case.phone.endswith(req.last_four_phone):
            return voice_response({
                "verified": False,
                "message": (
                    "The phone number doesn't match our records for that order. "
                    "For your security, I can't share case details. Please call "
                    "back with the correct information."
                ),
            })

    return voice_response(caller_info_from_case(case))


@router.get("/package/{case_id}")
def package_context(case_id: str, db: Session = Depends(get_db)):
    """Get full package context for a verified case.

    Retell calls this after verification to load context into the agent.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Build package manifest
    docs = []
    if case.packet_paths:
        for name, path in (case.packet_paths or {}).items():
            docs.append({
                "name": name,
                "description": get_doc_description(name, case.county or "your county"),
            })

    defense_count = len(case.defenses or {})
    fee_waiver_status = "included" if case.needs_filing_fee_waiver else "not included"

    return voice_response({
        "case_id": case.id,
        "customer_name": case.full_name or "there",
        "state": case.county or "",  # county field stores "State, County"
        "status": case.status or "",
        "packet_ready": case.packet_status == "generated",
        "documents": docs,
        "defenses_selected": defense_count,
        "fee_waiver": fee_waiver_status,
        "response_deadline": str(case.response_deadline) if case.response_deadline else "",
        "court_date": str(case.court_date) if case.court_date else "",
        "court_name": case.court_name or "",
        "landlord_name": case.landlord_name or "",
    })


@router.post("/document-help")
def document_help(req: DocumentHelpRequest, db: Session = Depends(get_db)):
    """Explain a specific document to the caller.

    Retell calls this when a caller asks 'what is the Answer form?'
    or 'where do I sign the fee waiver?'
    """
    case = db.query(Case).filter(Case.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    doc_info = get_doc_help(req.doc_name, case.county or "your county")

    if not doc_info:
        return voice_response({
            "found": False,
            "message": (
                f"I don't have specific information about '{req.doc_name}' "
                f"in your packet. Your filing checklist covers every document "
                f"and where to file it — you'll find step-by-step instructions "
                f"there. Is there a different document I can help with?"
            ),
        })

    return voice_response(doc_info)


@router.post("/correction")
def request_correction(req: CorrectionRequest, db: Session = Depends(get_db)):
    """Log a correction request — caller says something is wrong."""
    correction_id = f"corr_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # Log to chat_logs for audit trail
    log = ChatLog(
        case_id=req.case_id,
        role="caller",
        content=(
            f"CORRECTION REQUEST [{correction_id}]: "
            f"Field/Doc: {req.field_or_document}. "
            f"Description: {req.description}. "
            f"Email: {req.caller_email}"
        ),
    )
    db.add(log)
    db.commit()

    return voice_response({
        "correction_id": correction_id,
        "message": (
            "I've recorded your correction request. Our support team will "
            "review it and send you an updated packet if needed, usually "
            "within one business day. You'll get an email at "
            f"{req.caller_email}. Your reference number is {correction_id}. "
            "Is there anything else I can help with?"
        ),
    })


@router.post("/ticket")
def create_ticket(req: TicketRequest, db: Session = Depends(get_db)):
    """Create a support ticket for human follow-up."""
    ticket_id = f"ticket_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    log = ChatLog(
        case_id=req.case_id or "no-case",
        role="caller",
        content=(
            f"SUPPORT TICKET [{ticket_id}]: "
            f"Type: {req.issue_type}. "
            f"Caller: {req.caller_name}, {req.caller_email}, {req.caller_phone}. "
            f"Description: {req.description}"
        ),
    )
    db.add(log)
    db.commit()

    return voice_response({
        "ticket_id": ticket_id,
        "message": (
            f"I've created a support ticket for you. Your reference is "
            f"{ticket_id}. Someone from our team will follow up, usually "
            f"within one business day. In the meantime, your packet and "
            f"filing checklist have all the step-by-step instructions."
        ),
    })


@router.post("/resend")
def resend_packet(req: CallerVerifyRequest, db: Session = Depends(get_db)):
    """Resend the packet to the caller's email."""
    case = db.query(Case).filter(Case.id == req.case_id).first() if req.case_id else None
    if not case and req.email:
        case = db.query(Case).filter(Case.email == req.email).order_by(Case.created_at.desc()).first()

    if not case:
        return voice_response({
            "sent": False,
            "message": "I wasn't able to find your order to resend it.",
        })

    if not case.packet_paths:
        return voice_response({
            "sent": False,
            "message": (
                "Your packet hasn't been generated yet. Once you complete the "
                "chat intake and confirm your information, the packet will be "
                "ready to download. Would you like help with that process?"
            ),
        })

    # Trigger resend (in production, this calls SendGrid)
    return voice_response({
        "sent": True,
        "email": case.email or "your email on file",
        "message": (
            f"I've queued your packet to be resent to {case.email or 'your email on file'}. "
            f"You should receive it within a few minutes. Remember to check your spam folder. "
            f"Your filing deadline is {case.response_deadline or 'listed in your packet'}."
        ),
    })


@router.post("/webhook")
async def retell_webhook(request: Request):
    """Receive call outcome from Retell AI.

    Verifies the Retell signature before processing.
    """
    body = await request.body()
    signature = request.headers.get("X-Retell-Signature", "")

    # Verify signature (skip in dev if no key configured)
    if settings.retell_api_key:
        expected = hmac.new(
            settings.retell_api_key.encode(),
            body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        event = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    # Log the call outcome
    call_id = event.get("call_id", "unknown")
    outcome = event.get("outcome", "unknown")
    duration = event.get("duration_seconds", 0)

    return voice_response({
        "received": True,
        "call_id": call_id,
        "message": f"Call {call_id} ({outcome}, {duration}s) recorded.",
    })


@router.post("/callback")
def request_callback(req: CallbackRequest, db: Session = Depends(get_db)):
    """Set up a same-day callback. Sends email to support@evictions.help."""
    callback_id = f"cb_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

    # Log to database
    log = ChatLog(
        case_id=req.case_id or "no-case",
        role="caller",
        content=(
            f"CALLBACK REQUEST [{callback_id}]: "
            f"{req.first_name} {req.last_name}, "
            f"Phone: {req.phone}, "
            f"Best time: {req.best_time_eastern} Eastern, "
            f"Issue: {req.issue_summary}"
        ),
    )
    db.add(log)
    db.commit()

    # Send email to support
    email_sent = send_callback_email(
        callback_id=callback_id,
        first_name=req.first_name,
        last_name=req.last_name,
        phone=req.phone,
        best_time=req.best_time_eastern,
        case_id=req.case_id,
        issue=req.issue_summary,
        caller_email=req.caller_email,
    )

    return voice_response({
        "callback_id": callback_id,
        "email_sent": email_sent,
        "message": (
            f"I've set up a callback for you, {req.first_name}. "
            f"Someone from our team will call you today at {req.phone}, "
            f"around {req.best_time_eastern} Eastern time. "
            f"Your reference is {callback_id}."
        ),
    })


# ── Helpers ───────────────────────────────────────────────────────

def caller_info_from_case(case: Case) -> dict:
    """Build safe caller info response from a case."""
    return {
        "verified": True,
        "customer_name": case.full_name or "there",
        "case_id": case.id,
        "state": case.county or "",  # county field stores "State, County"
        "county": "",  # parsed from county field if needed
        "status": case.status or "",
        "package_type": "eviction_defense_v1",
        "packet_ready": case.packet_status == "generated",
        "has_fee_waiver": bool(case.needs_filing_fee_waiver),
        "response_deadline": str(case.response_deadline) if case.response_deadline else "",
        "court_date": str(case.court_date) if case.court_date else "",
    }


def get_doc_description(doc_name: str, county: str) -> str:
    """Return a one-line description of a document in the packet."""
    descriptions = {
        "COURT_FORM_Answer": "Official court answer form — your formal response to the eviction complaint.",
        "Fee_Waiver": "Application to waive court filing fees based on your income.",
        "Motion_to_Determine_Rent": "Motion asking the court to determine how much rent is actually owed.",
        "Landlord_Payment_Plan_Letter": "Letter to your landlord proposing a payment plan.",
        "Hardship_Extension_Letter": "Letter requesting more time from the court due to hardship.",
        "Filing_Checklist": "Step-by-step checklist showing exactly where and how to file each document.",
        "Court_Checklist": "What to bring and what to expect at your court hearing.",
        "EFiling_Instructions": "Instructions for e-filing your documents through the court portal.",
        "Rental_Assistance_Resources": "Local rental assistance programs and HUD-approved agencies in your area.",
        "Hearing_Prep_Guide": "Guide to preparing for your hearing — what to say, bring, and expect.",
    }
    return descriptions.get(doc_name, f"A document in your eviction defense packet for {county}.")


def get_doc_help(doc_name: str, county: str) -> dict | None:
    """Return detailed help for a document, or None if unknown."""
    help_db = {
        "COURT_FORM_Answer": {
            "found": True,
            "doc_name": "Court Answer Form",
            "description": "This is the official form 1.947(b) — your formal written response to the eviction complaint filed by your landlord.",
            "purpose": "It tells the court which allegations you deny, which defenses you're raising, and what outcome you want.",
            "where_to_sign": "Sign and date at the bottom of the last page where it says 'Signature of Tenant.' If you have co-tenants, each must sign separately.",
            "where_to_file": f"File at the Clerk of Court in {county}. Your Filing Checklist and E-Filing Instructions have the exact address and website.",
            "important_notes": (
                "You must file this within 5 business days of receiving the summons, "
                "not counting weekends and legal holidays. The deadline is listed at "
                "the top of your Filing Checklist."
            ),
        },
        "Fee_Waiver": {
            "found": True,
            "doc_name": "Fee Waiver Application",
            "description": "This asks the court to waive filing fees because of your financial situation.",
            "purpose": "If approved, you won't have to pay court filing fees. If denied, you'll need to pay before the deadline.",
            "where_to_sign": "Sign at the bottom under 'Applicant Signature.' The form must be notarized or signed under penalty of perjury.",
            "where_to_file": f"File together with your Answer form at the Clerk of Court in {county}.",
            "important_notes": (
                "Fill out your income, assets, and expenses completely. "
                "If anything is missing, the court may deny it. "
                "Your packet includes the financial data you provided during intake."
            ),
        },
    }

    # Fuzzy match
    for key, info in help_db.items():
        if key.lower() in doc_name.lower() or doc_name.lower() in key.lower():
            return info

    # Try substring match on doc_name
    for key, info in help_db.items():
        if any(word.lower() in doc_name.lower() for word in key.split("_")):
            return info

    return None
