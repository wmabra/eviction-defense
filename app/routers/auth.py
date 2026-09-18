"""Authentication endpoints — login, account info, and password change.

Account creation happens automatically after a successful payment (see the
payment router), not through a public registration endpoint.
"""
# pyright: reportAttributeAccessIssue=false
from datetime import datetime
from typing import Any, Optional, cast

from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.database.models import Case, User
from app.services.auth import (
    generate_temp_password,
    hash_password,
    sign_token,
    sign_verification_token,
    verify_password,
    verify_token,
    verify_verification_token,
)
from app.services.email_service import send_verification_email, send_welcome_email

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


# --------------------------------------------------------------------------- #
# Schemas
# --------------------------------------------------------------------------- #
class LoginRequest(BaseModel):
    email: str
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResendVerificationRequest(BaseModel):
    email: str


# --------------------------------------------------------------------------- #
# Helpers (also used by other routers)
# --------------------------------------------------------------------------- #
def create_user(db: Session, email: str, password: str) -> User:
    """Create a customer account. Commits and returns the refreshed user."""
    user = User(
        email=email.lower().strip(),
        password_hash=hash_password(password),
        must_change_password=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_current_user(
    authorization: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    """FastAPI dependency: resolve the authenticated user from a Bearer token."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Not authenticated")
    token = authorization[len("Bearer "):].strip()
    user_id = verify_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Account not found")
    return user


def _public_user(user: User) -> dict:
    return {
        "email": user.email,
        "must_change_password": bool(user.must_change_password),
    }


# --------------------------------------------------------------------------- #
# Status → progress (for the dashboard progress bar)
# --------------------------------------------------------------------------- #
STATUS_PROGRESS = {
    "pre_screen": 5,
    "payment_pending": 10,
    "intake_in_progress": 25,
    "intake_complete": 55,
    "extraction_pending": 65,
    "confirmation_pending": 75,
    "confirmation_complete": 85,
    "packet_ready": 100,
    "delivered": 100,
}


def progress_for(case: Case) -> int:
    """Return a 0-100 progress value for a case, preferring explicit progress."""
    progress = cast(Optional[int], case.progress)
    if progress:
        return progress
    status = cast(str, case.status or "")
    return STATUS_PROGRESS.get(status, 0)


# --------------------------------------------------------------------------- #
# Endpoints
# --------------------------------------------------------------------------- #
@router.post("/login")
def login(req: LoginRequest, db: Session = Depends(get_db)):
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    user = cast(Any, user)
    if not verify_password(req.password, cast(str, user.password_hash)):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user.last_login_at = datetime.utcnow()
    db.commit()

    return {"token": sign_token(user.id), "user": _public_user(user)}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Return the account, its latest case, progress, and download link."""
    case = (
        db.query(Case)
        .filter(Case.user_id == user.id)
        .order_by(Case.created_at.desc())
        .first()
    )

    case_data = None
    if case:
        status = cast(str, case.status or "")
        packet_status = cast(str, case.packet_status or "")
        packet_ready = status in ("intake_complete", "confirmation_pending", "confirmation_complete", "packet_ready", "delivered") or packet_status == "generated"
        case_data = {
            "id": case.id,
            "state": case.state,
            "county": case.county,
            "status": case.status,
            "progress": progress_for(case),
            "payment_status": case.payment_status,
            "packet_ready": packet_ready,
            "download_url": f"/api/v1/documents/download/{case.id}" if packet_ready else None,
        }

    return {"user": _public_user(user), "case": case_data}


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user = cast(Any, user)
    if not verify_password(req.current_password, cast(str, user.password_hash)):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    user.password_hash = hash_password(req.new_password)
    user.must_change_password = False
    db.commit()

    return {"status": "ok", "message": "Password updated"}


@router.post("/forgot-password")
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Reset a user's password: generate a new temp password and email it.

    Always returns success to avoid revealing whether an account exists.
    """
    email = req.email.lower().strip()
    user = db.query(User).filter(User.email == email).first()
    if user:
        user = cast(Any, user)
        temp_password = generate_temp_password()
        user.password_hash = hash_password(temp_password)
        user.must_change_password = True
        db.commit()
        from app.services.email_service import send_password_reset_email
        send_password_reset_email(email, temp_password)
    return {"status": "ok", "message": "If that email has an account, a new password has been sent."}


@router.get("/verify-email")
def verify_email(token: str, db: Session = Depends(get_db)):
    """Verify a customer's email and create their account (username = email)."""
    payload = verify_verification_token(token)
    if not payload:
        return HTMLResponse(
            "<h1>Link expired or invalid</h1>"
            "<p>This verification link is invalid or has expired. You can request a new one "
            "from your account page.</p>",
            status_code=400,
        )

    email = payload["email"]
    case_id = payload["case_id"]

    user = db.query(User).filter(User.email == email).first()
    temp_password: str | None = None
    if user is None:
        temp_password = generate_temp_password()
        user = create_user(db, email, temp_password)
    # else: already verified — don't reset their existing password.

    case = db.query(Case).filter(Case.id == case_id).first()
    if case is not None:
        case = cast(Any, case)  # SQLAlchemy Column descriptors aren't typed by pyright
        if case.user_id is None:
            case.user_id = user.id
        if case.status == "pending_email_verification":
            case.status = "intake_in_progress"
        db.commit()

    if temp_password:
        send_welcome_email(email, temp_password)

    return HTMLResponse(
        "<h1>Email verified!</h1>"
        "<p>Your account is ready. Check your inbox for your temporary password, then "
        "<a href='/account'>log in here</a>.</p>"
    )


@router.post("/resend-verification")
def resend_verification(req: ResendVerificationRequest, db: Session = Depends(get_db)):
    """Re-send the email-verification link for a pending order."""
    email = req.email.lower().strip()
    case = (
        db.query(Case)
        .filter(Case.email == email, Case.status == "pending_email_verification")
        .order_by(Case.created_at.desc())
        .first()
    )
    if case is None:
        # Always return success to avoid revealing whether an order exists.
        return {"status": "ok", "message": "If that email has a pending order, a new verification link has been sent."}

    case = cast(Any, case)
    token = sign_verification_token(email, str(case.id))
    verification_url = f"{settings.app_url.rstrip('/')}/api/v1/auth/verify-email?token={token}"
    send_verification_email(email, verification_url)
    return {"status": "ok", "message": "Verification email sent."}
