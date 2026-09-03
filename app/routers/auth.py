"""Authentication endpoints — login, account info, and password change.

Account creation happens automatically after a successful payment (see the
payment router), not through a public registration endpoint.
"""
# pyright: reportAttributeAccessIssue=false
from datetime import datetime
from typing import Optional, cast

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import Case, User
from app.services.auth import hash_password, sign_token, verify_password, verify_token

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
    if not user or not verify_password(req.password, user.password_hash):
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
    if not verify_password(req.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")

    user.password_hash = hash_password(req.new_password)
    user.must_change_password = False
    db.commit()

    return {"status": "ok", "message": "Password updated"}
