"""Admin dashboard API — case management, stats, and resend."""
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import Optional
import json

from app.database import get_db
from app.database.models import Case

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])

ADMIN_PASSWORD = "evictions2026"  # Change this in production!


class AdminAuth(BaseModel):
    password: str


@router.post("/auth")
def admin_auth(auth: AdminAuth):
    """Simple password auth for admin panel."""
    if auth.password == ADMIN_PASSWORD:
        return {"status": "ok", "token": "admin-session"}
    raise HTTPException(status_code=401, detail="Invalid password")


@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    """Get dashboard statistics."""
    total_cases = db.query(Case).count()
    
    # Cases today
    today = datetime.now().date()
    cases_today = db.query(Case).filter(
        Case.created_at >= today
    ).count()
    
    # Cases by status
    from sqlalchemy import func
    status_counts = dict(
        db.query(Case.status, func.count(Case.id))
        .group_by(Case.status)
        .all()
    )
    
    # Cases by state (from county field or extracted data)
    state_counts = {}
    
    # Revenue estimate ($299 per case with payment)
    paid_cases = status_counts.get("packet_ready", 0) + status_counts.get("delivered", 0)
    revenue_estimate = paid_cases * 299
    
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
                "created_at": str(c.created_at) if c.created_at else None,
                "defenses": json.loads(c.defenses) if c.defenses else {},
            }
            for c in cases
        ],
    }


@router.get("/cases/{case_id}")
def get_case(case_id: str, db: Session = Depends(get_db)):
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
        "defenses": json.loads(case.defenses) if case.defenses else {},
        "status": case.status,
        "payment_status": case.payment_status,
        "created_at": str(case.created_at) if case.created_at else None,
    }


@router.post("/cases/{case_id}/resend")
def resend_packet(case_id: str, db: Session = Depends(get_db)):
    """Regenerate and return a download URL for a case's packet."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    
    # Build the data dict for packet generation
    params = "&".join([
        f"full_name={case.full_name or 'Tenant'}",
        f"county={case.county or ''}",
        f"state=FL",
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
def list_chat_sessions(page: int = 1, limit: int = 20, db: Session = Depends(get_db)):
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
def get_chat_session_log(case_id: str, db: Session = Depends(get_db)):
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
