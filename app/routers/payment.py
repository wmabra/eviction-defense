"""Payment API endpoints — Authorize.net."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.payment import charge_card, PaymentResult

router = APIRouter(prefix="/api/v1/payment", tags=["payment"])


class PaymentRequest(BaseModel):
    opaque_data: dict  # Accept.js opaqueData object
    order_id: str
    customer_email: str
    customer_name: str = ""


class PaymentResponse(BaseModel):
    success: bool
    transaction_id: str | None = None
    message: str = ""
    auth_code: str | None = None


@router.post("/charge", response_model=PaymentResponse)
def process_payment(req: PaymentRequest):
    """Process a payment via Authorize.net."""
    if not req.opaque_data.get("dataDescriptor") or not req.opaque_data.get("dataValue"):
        raise HTTPException(status_code=400, detail="Invalid payment data. Please try again.")
    
    result: PaymentResult = charge_card(
        opaque_data=req.opaque_data,
        amount_cents=39500,  # $395.00
        order_id=req.order_id,
        customer_email=req.customer_email,
        description=f"Eviction Defense Packet — {req.customer_name}"
    )
    
    if not result.success:
        raise HTTPException(status_code=402, detail=result.message)
    
    return PaymentResponse(
        success=True,
        transaction_id=result.transaction_id,
        message=result.message,
        auth_code=result.auth_code,
    )
