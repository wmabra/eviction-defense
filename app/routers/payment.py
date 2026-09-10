"""Payment API endpoints — Authorize.net (optional).

On a successful charge we automatically create the customer account and their
case, then email them their login credentials (username = email + generated
password). The client then redirects the user to the /account login screen.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.database.models import Case, User
from app.routers.auth import create_user
from app.services.auth import generate_temp_password
from app.services.email_service import send_welcome_email

# authorizenet is a declared dependency but may not be installed in every
# environment (e.g. local dev). Degrade to a 503 at request time instead of
# failing at import time.
try:
    from app.services.payment import charge_card as _charge_card
except ImportError:  # pragma: no cover — authorizenet not installed
    _charge_card = None

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])


class PaymentRequest(BaseModel):
    opaque_data: dict  # Accept.js opaqueData object
    order_id: str
    customer_email: str
    customer_name: str = ""
    # Eligibility + address collected before payment (used to create the case)
    state: str
    county: str
    property_address: str = ""
    property_city: str = ""
    property_zip: str = ""


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str | None = None
    message: str = ""
    auth_code: str | None = None
    email: str = ""
    temp_password: str | None = None  # only set when a NEW account was created


@router.post("/charge", response_model=PaymentResponse)
def process_payment(req: PaymentRequest, db: Session = Depends(get_db)):
    """Process a payment, then provision the account + case on success."""
    if _charge_card is None:
        raise HTTPException(status_code=503, detail="Payment processing is not available.")
    if not settings.authorize_login_id or not settings.authorize_transaction_key:
        raise HTTPException(status_code=503, detail="Payment processing is not configured.")
    if not req.opaque_data.get("dataDescriptor") or not req.opaque_data.get("dataValue"):
        raise HTTPException(status_code=400, detail="Invalid payment data. Please try again.")

    result = _charge_card(
        opaque_data=req.opaque_data,
        amount_cents=29900,  # $299.00 flat — same price for all 20 states
        order_id=req.order_id,
        customer_email=req.customer_email,
        description=f"Eviction Defense Packet — {req.customer_name}"
    )

    if not result.success:
        raise HTTPException(status_code=402, detail=result.message)

    # --- Payment succeeded: create/find account + case, email credentials ---
    email = req.customer_email.lower().strip()

    user = db.query(User).filter(User.email == email).first()
    temp_password: str | None = None
    if user is None:
        temp_password = generate_temp_password()
        user = create_user(db, email, temp_password)
    # Existing account: reuse it and do NOT reset their password.

    case = Case(
        user_id=user.id,
        state=(req.state or "").upper(),
        county=req.county or "",
        property_address=req.property_address or "",
        property_city=req.property_city or "",
        property_zip=req.property_zip or "",
        email=email,
        full_name=req.customer_name or None,
        eligible=True,
        payment_status="paid",
        status="intake_in_progress",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    if temp_password:
        send_welcome_email(email, temp_password)

    return PaymentResponse(
        success=True,
        transaction_id=result.transaction_id,
        message="Payment complete. Your account is ready — check your email for your password.",
        auth_code=result.auth_code,
        email=email,
        temp_password=temp_password,
    )
