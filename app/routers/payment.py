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
from app.services.auth import sign_verification_token
from app.services.email_service import send_verification_email

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
    state: str = ""
    county: str = ""
    property_address: str = ""
    property_city: str = ""
    property_zip: str = ""
    served: str = "yes"


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str | None = None
    message: str = ""
    auth_code: str | None = None
    email: str = ""
    needs_verification: bool = False  # True for a NEW customer (verify before account)


@router.post("/charge", response_model=PaymentResponse)
def process_payment(req: PaymentRequest, db: Session = Depends(get_db)):
    """Process a payment, then provision the account + case on success."""
    if (req.served or "").strip().lower() in ("no", "false", "0"):
        raise HTTPException(
            status_code=400,
            detail="You must have received court eviction papers (summons and complaint) or have an active case number to use this service. We cannot prepare court filings until an eviction lawsuit has actually been filed in court."
        )
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

    # --- Payment succeeded: create the case; verify email before account ---
    email = req.customer_email.lower().strip()

    # Returning customer (already has an account): link the new case and skip
    # verification. New customer: defer account creation until they verify.
    existing_user = db.query(User).filter(User.email == email).first()

    case = Case(
        user_id=existing_user.id if existing_user else None,
        state=(req.state or "").upper(),
        county=req.county or "",
        property_address=req.property_address or "",
        property_city=req.property_city or "",
        property_zip=req.property_zip or "",
        email=email,
        full_name=req.customer_name or None,
        eligible=True,
        payment_status="paid",
        status="intake_in_progress" if existing_user else "pending_email_verification",
    )
    db.add(case)
    db.commit()
    db.refresh(case)

    if existing_user is None:
        # New customer: send a verification link. The account (and its password)
        # is created only after they click it.
        token = sign_verification_token(email, str(case.id))
        verification_url = f"{settings.app_url.rstrip('/')}/api/v1/auth/verify-email?token={token}"
        send_verification_email(email, verification_url)

    return PaymentResponse(
        success=True,
        transaction_id=result.transaction_id,
        message=(
            "Payment complete. Check your email to verify your account."
            if existing_user is None
            else "Payment complete. Log in to continue."
        ),
        auth_code=result.auth_code,
        email=email,
        needs_verification=existing_user is None,
    )
