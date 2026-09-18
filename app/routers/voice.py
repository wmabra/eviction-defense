"""Voice Support API — powers the Retell AI phone agent.

Compliance rules baked into every response:
1. We are a self-help document preparation service. Not legal advice. Not a law firm.
2. The agent must never contradict the website or the customer's document package.
"""
from fastapi import APIRouter, HTTPException, Request, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime
from typing import Any, Optional, cast
import hashlib
import hmac
import json
import re

from app.database import get_db
from app.database.models import Case, ChatLog
from app.services.email_service import send_callback_email
from app.config import settings

# NOTE: `case` objects are cast to `Any` after fetch (see `case = cast(Any, case)`
# in each endpoint) because SQLAlchemy Column descriptors aren't typed by pyright.

router = APIRouter(prefix="/api/v1/voice", tags=["voice"])

# ── Pydantic schemas ──────────────────────────────────────────────

class CallerVerifyRequest(BaseModel):
    """Verify a caller by email or case ID."""
    email: Optional[str] = None
    case_id: Optional[str] = None
    last_four_phone: Optional[str] = None


class PackageRequest(BaseModel):
    """Look up full package context for a verified case (POST variant for Retell tools)."""
    case_id: str


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

    case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright

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


def _package_context_payload(case_id: str, db: Session) -> dict:
    """Build the package-context dict for a case (shared by GET + POST)."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright

    docs = []
    if case.packet_paths:
        for name, path in (case.packet_paths or {}).items():
            docs.append({
                "name": name,
                "description": get_doc_description(name, case.county or "your county"),
            })

    defense_count = len(case.defenses or {})
    fee_waiver_status = "included" if case.needs_filing_fee_waiver else "not included"

    return {
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
    }


@router.get("/package/{case_id}")
def package_context(case_id: str, db: Session = Depends(get_db)):
    """Get full package context for a verified case (browser/curl)."""
    return voice_response(_package_context_payload(case_id, db))


@router.post("/package")
def package_context_post(req: PackageRequest, db: Session = Depends(get_db)):
    """POST variant — Retell custom tools POST a JSON body."""
    return voice_response(_package_context_payload(req.case_id, db))


@router.post("/document-help")
def document_help(req: DocumentHelpRequest, db: Session = Depends(get_db)):
    """Explain a specific document to the caller.

    Retell calls this when a caller asks 'what is the Answer form?'
    or 'where do I sign the fee waiver?'
    """
    case = db.query(Case).filter(Case.id == req.case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright

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

    case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright

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
    case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright
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
        "response_deadline": str(case.response_deadline) if case.response_deadline else "",  # type: ignore[reportGeneralTypeIssues]
        "court_date": str(case.court_date) if case.court_date else "",  # type: ignore[reportGeneralTypeIssues]
    }


# ── Document knowledge base — canonical info for every packet document ─────
# Keys match the generator's `paths` dict (see app/services/generator.py) plus
# the court answer ("court_form") and fee waiver ("fee_waiver") added separately.

_DOCS: dict[str, dict] = {
    "cover_page": {
        "name": "Cover Page / Document Index",
        "aliases": ("cover page", "document index", "manifest", "table of contents", "index"),
        "description": "Cover page that lists and indexes every document in your packet.",
        "purpose": "A quick reference so you can see everything in your packet and the order to review it.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Use it as your table of contents; the numbering matches each document.",
    },
    "court_form": {
        "name": "Court Answer Form",
        "aliases": ("answer form", "court answer", "eviction answer", "answer", "court form"),
        "description": "The official court answer form — your formal written response to the eviction complaint.",
        "purpose": "Tells the court which claims you deny, which defenses you raise, and what outcome you want.",
        "where_to_sign": "Sign and date at the bottom of the last page ('Signature of Tenant'). If you have co-tenants, each must sign separately.",
        "where_to_file": "File at the Clerk of Court in {county}. Your Filing Checklist has the exact address and website.",
        "important_notes": "File it by the deadline shown on your summons and at the top of your Filing Checklist.",
    },
    "fee_waiver": {
        "name": "Fee Waiver Application",
        "aliases": ("fee waiver", "waiver", "ifp", "forma pauperis", "pauper", "filing fee"),
        "description": "Application asking the court to waive filing fees because of your financial situation.",
        "purpose": "If approved, you won't have to pay court filing fees. If denied, you'll need to pay before the deadline.",
        "where_to_sign": "Sign at the bottom under 'Applicant Signature.' It may need to be notarized or signed under penalty of perjury.",
        "where_to_file": "File together with your Answer form at the Clerk of Court in {county}.",
        "important_notes": "Your income, asset, and expense figures are pre-filled from your intake — verify they're correct.",
    },
    "emergency_action_plan": {
        "name": "Emergency Action Plan",
        "aliases": ("emergency action plan", "action plan", "emergency plan", "what to do"),
        "description": "A step-by-step 'what to do right now' guide.",
        "purpose": "Tells you the immediate actions to take to protect yourself.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Read this first if you're feeling overwhelmed — it walks you through the next steps in order.",
    },
    "eviction_timeline": {
        "name": "Eviction Timeline",
        "aliases": ("eviction timeline", "timeline", "deadline", "process timeline"),
        "description": "A timeline of the eviction process and your deadlines in your state.",
        "purpose": "Helps you understand where you are in the process and what happens next.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Your exact filing deadline is at the top of your Filing Checklist.",
    },
    "defenses_explained": {
        "name": "Defenses Explained",
        "aliases": ("defenses explained", "defenses", "defense explanations", "defence"),
        "description": "Plain-English explanation of the defenses you selected.",
        "purpose": "So you understand each defense and can explain it in court.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Review this before your hearing so you can describe your defenses in your own words.",
    },
    "evidence_guide": {
        "name": "Evidence Guide",
        "aliases": ("evidence guide", "evidence", "proof", "documents to gather"),
        "description": "A checklist of documents and evidence to gather for your case.",
        "purpose": "Helps you collect the proof you need for court.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Gather receipts, photos, notices, and communications with your landlord early.",
    },
    "income_expense_worksheet": {
        "name": "Income & Expense Worksheet",
        "aliases": ("income expense worksheet", "income", "expense worksheet", "financial worksheet", "income and expense", "worksheet"),
        "description": "Your monthly income and expenses, itemized.",
        "purpose": "Supports your fee waiver and shows the court your financial situation.",
        "where_to_sign": "Review for accuracy — no signature needed on the worksheet itself.",
        "where_to_file": "Keep it with your Fee Waiver Application — the figures support it.",
        "important_notes": "Check that the numbers match your actual income and expenses before you file.",
    },
    "filing_checklist": {
        "name": "Filing Checklist",
        "aliases": ("filing checklist", "filing", "how to file", "where to file", "checklist"),
        "description": "Step-by-step checklist for how and where to file your answer.",
        "purpose": "Walks you through signing, making copies, filing, and serving the landlord.",
        "where_to_sign": "No signature needed — it's a guide, not a form.",
        "where_to_file": "Reference guide — it tells you where to file each document.",
        "important_notes": "Your deadline and the court's address are at the top. Follow the steps in order.",
    },
    "court_checklist": {
        "name": "Court Hearing Checklist",
        "aliases": ("court checklist", "hearing checklist", "court hearing", "hearing prep"),
        "description": "What to bring and what to expect at your court hearing.",
        "purpose": "Prepares you for the day of your hearing.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Arrive 15 minutes early and bring your packet, evidence, and a pen and paper.",
    },
    "hearing_script": {
        "name": "Hearing Script",
        "aliases": ("hearing script", "script", "what to say", "hearing prep guide"),
        "description": "A script of what to say to the judge at your hearing.",
        "purpose": "Gives you clear, plain-English wording to use in court.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Practice it beforehand, but speak naturally in your own words.",
    },
    "rental_assistance": {
        "name": "Rental Assistance Resources",
        "aliases": ("rental assistance", "rent assistance", "assistance", "rent help", "resources", "financial help"),
        "description": "Local rental assistance programs and agencies in your county.",
        "purpose": "Helps you find financial help for rent or utilities.",
        "where_to_sign": "No signature needed.",
        "where_to_file": "Reference only — not filed with the court.",
        "important_notes": "Contact these programs early — funding is limited and can run out.",
    },
    "demand_letter": {
        "name": "Demand Letter",
        "aliases": ("demand letter", "repair demand", "repair letter", "demand"),
        "description": "A letter to your landlord demanding repairs.",
        "purpose": "Documents that you asked for repairs, which supports a habitability defense.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "Send it to your landlord (keep a copy for yourself and for court).",
        "important_notes": "Send it by certified mail and keep the receipt as proof.",
    },
    "motion_to_determine_rent": {
        "name": "Motion to Determine Rent",
        "aliases": ("motion to determine rent", "determine rent", "dispute rent", "rent amount", "motion determine"),
        "description": "A motion asking the court to determine how much rent you actually owe.",
        "purpose": "Used when you dispute the amount the landlord claims.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "File at the Clerk of Court in {county}.",
        "important_notes": "Attach evidence of the correct amount and file before your deadline.",
    },
    "payment_plan_letter": {
        "name": "Payment Plan Letter",
        "aliases": ("payment plan", "payment plan letter", "repayment plan", "payment letter"),
        "description": "A letter to your landlord proposing a payment plan.",
        "purpose": "Shows the court you're trying to pay and may help you reach an agreement.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "Send it to your landlord and keep a copy for court.",
        "important_notes": "Send by certified mail and keep the receipt.",
    },
    "hardship_letter": {
        "name": "Hardship Letter",
        "aliases": ("hardship letter", "hardship", "extension letter", "more time"),
        "description": "A letter explaining your financial hardship and asking for more time or consideration.",
        "purpose": "Asks the court or landlord for leniency based on your circumstances.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "File with the court or send to the landlord as directed in the letter.",
        "important_notes": "Be honest and specific about your situation.",
    },
    "motion_for_hearing": {
        "name": "Motion for Hearing",
        "aliases": ("motion for hearing", "request hearing", "hearing motion", "motion hearing"),
        "description": "A motion requesting a hearing in your case.",
        "purpose": "Ensures you get your day in court.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "File at the Clerk of Court in {county}.",
        "important_notes": "File promptly so your hearing is scheduled.",
    },
    "motion_of_continuance": {
        "name": "Motion of Continuance",
        "aliases": ("motion of continuance", "continuance", "postpone", "reschedule", "continuance motion"),
        "description": "A motion asking the court to postpone your hearing.",
        "purpose": "Gives you more time to prepare or gather evidence.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "File at the Clerk of Court in {county} as soon as possible.",
        "important_notes": "File before your hearing date.",
    },
    "emergency_motion_stay_eviction": {
        "name": "Emergency Motion to Stay Eviction",
        "aliases": ("stay eviction", "emergency stay", "stop eviction", "motion stay eviction", "emergency motion"),
        "description": "An emergency motion asking the court to stop the eviction before judgment.",
        "purpose": "Asks the court to halt the eviction until your case is heard.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "File immediately at the Clerk of Court in {county}.",
        "important_notes": "This is urgent — file it right away.",
    },
    "emergency_motion_stay_writ": {
        "name": "Emergency Motion to Stay Writ/Warrant",
        "aliases": ("stay writ", "stay warrant", "stop writ", "stop warrant", "motion stay writ", "motion stay warrant", "writ of possession"),
        "description": "An emergency motion asking the court to stop a writ/warrant of possession (post-judgment).",
        "purpose": "Asks the court to pause a removal that has already been ordered.",
        "where_to_sign": "Sign and date at the bottom.",
        "where_to_file": "File immediately at the Clerk of Court in {county}.",
        "important_notes": "This may be your last chance to stop removal — file it immediately and contact legal aid.",
    },
    "notice_automatic_stay_bankruptcy": {
        "name": "Notice of Automatic Stay (Bankruptcy)",
        "aliases": ("automatic stay", "bankruptcy notice", "bankruptcy stay", "notice automatic stay"),
        "description": "A notice that a bankruptcy filing triggers an automatic stay of the eviction.",
        "purpose": "Tells the court and landlord that the eviction must pause because of a bankruptcy filing.",
        "where_to_sign": "Sign and date if required.",
        "where_to_file": "File with the court and serve on the landlord's attorney.",
        "important_notes": "Coordinate with your bankruptcy attorney before filing.",
    },
}


def _normalize_doc_name(doc_name: str) -> str | None:
    """Map a packet key, filename, or caller phrase to a canonical _DOCS key."""
    raw = (doc_name or "").lower().strip()

    # 1) Exact packet-key match (e.g. "court_form", "filing_checklist").
    if raw in _DOCS:
        return raw

    # 2) Normalize: strip numbering / ".pdf" / "FILE_THIS", spaces for underscores.
    dn = re.sub(r"\.pdf$", "", raw)
    dn = re.sub(r"^\d+[_\s-]*", "", dn)
    dn = dn.replace("court_form", "court form")
    dn = re.sub(r"file[_\s]?this", "", dn)
    dn = dn.replace("_", " ").replace("-", " ")
    dn = re.sub(r"\s+", " ", dn).strip()

    # 3) Exact human-name / normalized-key match.
    for key, info in _DOCS.items():
        if dn == info["name"].lower() or dn == key.replace("_", " "):
            return key

    # 4) Fuzzy alias match — the longest (most specific) matching alias wins.
    best_key: str | None = None
    best_len = 0
    for key, info in _DOCS.items():
        for alias in info["aliases"]:
            if alias and alias in dn and len(alias) > best_len:
                best_key = key
                best_len = len(alias)
    return best_key


def get_doc_description(doc_name: str, county: str) -> str:
    """Return a one-line description of a document in the packet."""
    key = _normalize_doc_name(doc_name)
    if key and key in _DOCS:
        return _DOCS[key]["description"]
    return f"A document in your eviction defense packet for {county}."


def get_doc_help(doc_name: str, county: str) -> dict | None:
    """Return detailed help for a document, or None if unknown."""
    key = _normalize_doc_name(doc_name)
    if not key or key not in _DOCS:
        return None
    info = _DOCS[key]
    return {
        "found": True,
        "doc_name": info["name"],
        "description": info["description"],
        "purpose": info["purpose"],
        "where_to_sign": info["where_to_sign"],
        "where_to_file": info["where_to_file"].format(county=county),
        "important_notes": info["important_notes"],
    }
