"""Admin dashboard API — case management, stats, and resend."""
from fastapi import APIRouter, HTTPException, Depends, Header, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional, cast
import json

from app.database import get_db
from app.database.models import Case
from app.config import settings

def _dt_str(value: Optional[datetime]) -> Optional[str]:
    """Format a datetime for JSON, or None."""
    return str(value) if value is not None else None


def _load_defenses(value: object) -> dict:
    """Return a case's defenses as a dict (JSON columns may hold dict or str)."""
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return {}
    return {}


router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

def require_admin(x_admin_password: str = Header(default="", alias="X-Admin-Password")):
    """Dependency: gate admin endpoints by password via the X-Admin-Password header."""
    if x_admin_password != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid admin password")
    return True


def _default_test_data(state: str, county: str, full_name: str) -> dict:
    """A complete, valid test case so a packet can be generated with minimal input."""
    return {
        "state": state.upper(),
        "personal_info": {
            "full_name": full_name or "Test Tenant",
            "phone": "(555) 123-4567",
            "email": "test@evictions.help",
            "property_address": "123 Main St",
            "property_city": "Springfield",
            "property_zip": "00000",
            "county": county or "",
        },
        "landlord_info": {
            "landlord_name": "Test Landlord LLC",
            "landlord_address": "456 Owner Blvd",
            "landlord_phone": "(555) 999-9999",
            "landlord_email": "owner@example.com",
        },
        "case_details": {
            "case_number": "TEST-2024-0001",
            "court_name": f"{county or 'Your'} Court",
            "complaint_amount_claimed": "$2,400.00",
            "summons_service_date": "2024-06-01",
            "response_deadline": "2024-06-10",
        },
        "rent_payment": {
            "monthly_rent": 1200.0,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 600.0,
        },
        "defenses": {
            "def_repairs": {"checked": True, "explanation": "Heat broken since January."},
            "def_amount": {"checked": True, "explanation": "Already paid half."},
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
        },
        "financial_info": {
            "monthly_gross_income": 2400.0,
            "employment_income": 2400.0,
            "rent_or_mortgage": 1200.0,
            "utilities_expense": 150.0,
            "food_expense": 300.0,
            "household_adults": 1,
            "household_children": 0,
            "receives_snap": False,
            "receives_medicaid": True,
        },
    }


class AdminAuth(BaseModel):
    password: str


@router.post("/generate-test-packet")
async def generate_test_packet(request: Request):
    """Admin: generate a full test document package from arbitrary data.

    Lets Mark/William generate any packet on demand (unlimited, no customer
    account needed). Requires the admin password in the JSON body.

    Body may be just {"password": "...", "state": "VA", "county": "Fairfax",
    "full_name": "Test Tenant"} — everything else is filled with valid defaults —
    or include any of personal_info / landlord_info / case_details / rent_payment /
    defenses / preferences / financial_info to override specific sections.
    """
    import json as _json
    try:
        body = await request.json()
    except Exception:
        body = {}

    if body.get("password") != settings.admin_password:
        raise HTTPException(status_code=401, detail="Invalid admin password")

    pi = body.get("personal_info") or {}
    state = str(body.get("state") or "VA").upper()
    county = body.get("county") or pi.get("county") or ""
    full_name = body.get("full_name") or pi.get("full_name") or "Test Tenant"

    data = _default_test_data(state, county, full_name)
    for section in ("personal_info", "landlord_info", "case_details", "rent_payment", "defenses", "preferences", "financial_info"):
        override = body.get(section)
        if isinstance(override, dict):
            data[section].update(override)

    from app.routers.documents import _build_and_return_packet
    dpi = data["personal_info"]
    dli = data["landlord_info"]
    dcd = data["case_details"]
    return _build_and_return_packet(
        full_name, county, state,
        dpi.get("property_address", ""), dli.get("landlord_name", ""),
        dcd.get("case_number", ""), dpi.get("phone", ""), dpi.get("email", ""),
        extra_data=data,
    )


@router.post("/auth")
def admin_auth(auth: AdminAuth):
    """Simple password auth for admin panel."""
    if auth.password == settings.admin_password:
        return {"status": "ok", "token": "admin-session"}
    raise HTTPException(status_code=401, detail="Invalid password")


@router.get("/stats")
def get_stats(db: Session = Depends(get_db), _: bool = Depends(require_admin)):
    """Get dashboard statistics."""
    total_cases = db.query(Case).count()
    
    # Cases today
    today = datetime.now().date()
    cases_today = db.query(Case).filter(
        Case.created_at >= today
    ).count()
    
    # Cases by status
    from sqlalchemy import func
    status_counts = {
        str(status): count
        for status, count in db.query(Case.status, func.count(Case.id)).group_by(Case.status).all()
    }

    # Cases by state (from the `state` column added with account flow)
    state_counts = {
        str(state): count
        for state, count in db.query(Case.state, func.count(Case.id))
        .filter(Case.state.isnot(None))
        .group_by(Case.state)
        .all()
    }

    # Revenue estimate ($399 per paid case)
    paid_cases = db.query(Case).filter(Case.payment_status == "paid").count()
    revenue_estimate = paid_cases * 399
    
    return {
        "total_cases": total_cases,
        "cases_today": cases_today,
        "revenue_estimate": revenue_estimate,
        "status_breakdown": status_counts,
        "state_breakdown": state_counts,
    }


@router.get("/cases")
def list_cases(
    page: int = 1,
    limit: int = 50,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    _: bool = Depends(require_admin),
):
    """List all cases with pagination and filtering."""
    query = db.query(Case).order_by(Case.created_at.desc())
    
    if status:
        query = query.filter(Case.status == status)
    
    total = query.count()
    cases = query.offset((page - 1) * limit).limit(limit).all()
    
    return {
        "total": total,
        "page": page,
        "cases": [
            {
                "id": c.id,
                "full_name": c.full_name,
                "email": c.email,
                "phone": c.phone,
                "county": c.county,
                "case_number": c.case_number,
                "landlord_name": c.landlord_name,
                "status": c.status,
                "payment_status": c.payment_status,
                "created_at": _dt_str(cast(Optional[datetime], c.created_at)),
                "defenses": _load_defenses(cast(Optional[object], c.defenses)),
            }
            for c in cases
        ],
    }


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db), _: bool = Depends(require_admin)):
    """Get detailed info for a single case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    return {
        "id": case.id,
        "full_name": case.full_name,
        "email": case.email,
        "phone": case.phone,
        "property_address": case.property_address,
        "property_city": case.property_city,
        "property_zip": case.property_zip,
        "county": case.county,
        "case_number": case.case_number,
        "court_name": case.court_name,
        "landlord_name": case.landlord_name,
        "landlord_address": case.landlord_address,
        "landlord_phone": case.landlord_phone,
        "landlord_email": case.landlord_email,
        "landlord_attorney_name": case.landlord_attorney_name,
        "complaint_amount_claimed": case.complaint_amount_claimed,
        "monthly_rent": case.monthly_rent,
        "defenses": _load_defenses(cast(Optional[object], case.defenses)),
        "status": case.status,
        "payment_status": case.payment_status,
        "created_at": _dt_str(cast(Optional[datetime], case.created_at)),
    }


@router.post("/cases/{case_id}/resend")
def resend_packet(case_id: str, db: Session = Depends(get_db), _: bool = Depends(require_admin)):
    """Regenerate and return a download URL for a case's packet."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Build the data dict for packet generation
    params = "&".join([
        f"full_name={case.full_name or 'Tenant'}",
        f"county={case.county or ''}",
        f"state={case.state or ''}",
        f"property_address={case.property_address or ''}",
        f"landlord_name={case.landlord_name or ''}",
        f"case_number={case.case_number or ''}",
        f"phone={case.phone or ''}",
        f"email={case.email or ''}",
    ])
    
    return {
        "status": "ok",
        "case_id": case_id,
        "download_url": f"/api/v1/documents/generate-packet?{params}",
    }


@router.get("/chat-sessions")
def list_chat_sessions(page: int = 1, limit: int = 20, db: Session = Depends(get_db), _: bool = Depends(require_admin)):
    """List recent chat sessions for review."""
    from app.database.models import ChatLog
    from sqlalchemy import func, distinct
    
    # Get unique case_ids with latest message time
    sessions = db.query(
        ChatLog.case_id,
        func.max(ChatLog.created_at).label("last_message"),
        func.count(ChatLog.id).label("message_count")
    ).group_by(ChatLog.case_id).order_by(func.max(ChatLog.created_at).desc()).offset((page-1)*limit).limit(limit).all()
    
    return {
        "sessions": [
            {"case_id": s.case_id, "last_message": str(s.last_message), "message_count": s.message_count}
            for s in sessions
        ]
    }


@router.get("/chat-sessions/{case_id}")
def get_chat_session_log(case_id: str, db: Session = Depends(get_db), _: bool = Depends(require_admin)):
    """Get the full chat log for a specific session."""
    from app.database.models import ChatLog
    
    messages = db.query(ChatLog).filter(ChatLog.case_id == case_id).order_by(ChatLog.created_at.asc()).all()
    
    return {
        "case_id": case_id,
        "messages": [
            {"role": m.role, "content": m.content, "time": str(m.created_at)}
            for m in messages
        ]
    }
