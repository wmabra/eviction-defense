"""Intake questionnaire API endpoints."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import Case
from app.schema.intake import PreScreen, PreScreenResult, CompleteIntake
from app.services.eligibility import check_eligibility

router = APIRouter(prefix="/api/v1/intake", tags=["intake"])


@router.post("/pre-screen", response_model=PreScreenResult)
def pre_screen(screen: PreScreen):
    """Check eligibility before accepting payment."""
    result = check_eligibility(screen)
    return PreScreenResult(**result)


@router.post("/submit")
def submit_intake(payload: CompleteIntake, case_id: str, db: Session = Depends(get_db)):
    """Submit complete intake questionnaire for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        case = Case(id=case_id, county=payload.personal_info.county, status="intake_in_progress")
        db.add(case)

    # Update case with intake data
    p = payload.personal_info
    case.full_name = p.full_name
    case.phone = p.phone
    case.email = p.email
    case.property_address = p.property_address
    case.property_city = p.property_city
    case.property_zip = p.property_zip
    case.mailing_address = p.mailing_address
    case.co_tenants = p.co_tenants

    l = payload.landlord_info
    case.landlord_name = l.landlord_name
    case.landlord_address = l.landlord_address
    case.landlord_phone = l.landlord_phone
    case.landlord_email = l.landlord_email
    case.landlord_attorney_name = l.landlord_attorney_name
    case.landlord_attorney_email = l.landlord_attorney_email

    c = payload.case_details
    case.case_number = c.case_number
    case.court_name = c.court_name
    case.received_3day_notice = c.received_3day_notice
    case.notice_received_date = c.notice_received_date
    case.notice_amount_demanded = c.notice_amount_demanded
    case.received_summons = c.received_summons
    case.summons_service_date = c.summons_service_date
    case.complaint_amount_claimed = c.complaint_amount_claimed
    case.court_date = c.court_date

    r = payload.rent_payment
    case.monthly_rent = r.monthly_rent
    case.agree_with_amount = r.agree_with_amount
    case.amount_tenant_believes_owed = r.amount_tenant_believes_owed

    case.defenses = payload.defenses.model_dump(mode="json")
    case.status = "intake_complete"

    db.commit()
    return {"status": "ok", "case_id": case_id}


@router.get("/status/{case_id}")
def get_intake_status(case_id: str, db: Session = Depends(get_db)):
    """Get current intake status and next steps."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    stages = {
        "pre_screen": "Eligibility check",
        "payment_pending": "Awaiting payment",
        "intake_in_progress": "Complete questionnaire",
        "intake_complete": "Upload documents",
        "extraction_pending": "Processing documents",
        "confirmation_pending": "Confirm case details",
        "packet_ready": "Packet ready to download",
        "delivered": "Packet delivered",
    }

    return {
        "case_id": case.id,
        "status": case.status,
        "stage_description": stages.get(case.status, "Unknown"),
        "payment_status": case.payment_status,
        "extraction_confirmed": case.extraction_confirmed,
        "packet_status": case.packet_status,
    }
