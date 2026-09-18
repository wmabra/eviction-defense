#!/usr/bin/env python3
"""Verify the account flow end-to-end (payment → verify → login → me).

Runs against a throwaway SQLite DB (test_account_flow.db) and mocks the
Authorize.net gateway so no real charge happens. Prints PASS/FAIL per step.
"""
import logging
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

os.environ["DATABASE_URL"] = "sqlite:///./test_account_flow.db"

from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal, init_db
from app.database.models import Case, User
from app.services.auth import sign_verification_token

# Fresh DB
for _f in ("test_account_flow.db",):
    try:
        os.remove(_f)
    except FileNotFoundError:
        pass
init_db()

# Mock the payment gateway (authorizenet isn't installed locally).
import app.routers.payment as payment

payment._charge_card = lambda **kwargs: SimpleNamespace(
    success=True, transaction_id="txn_test_001", message="ok", auth_code="AUTH01"
)

# Capture the email bodies so we can confirm the verification + welcome emails
# and extract the temp password.
captured: list[str] = []


class CaptureHandler(logging.Handler):
    def emit(self, record):
        captured.append(record.getMessage())


logging.getLogger("app.services.email_service").addHandler(CaptureHandler())
logging.getLogger("app.services.email_service").setLevel(logging.INFO)

client = TestClient(app)
EMAIL = "jane.doe.qa@example.com"

PASS: list[str] = []
FAIL: list[str] = []


def check(name: str, cond: bool):
    print(f"  [{'PASS' if cond else 'FAIL'}] {name}")
    (PASS if cond else FAIL).append(name)


# ── 1. Payment ───────────────────────────────────────────────────────────────
print("=== 1. Payment (/charge) ===")
resp = client.post("/api/v1/payment/charge", json={
    "opaque_data": {"dataDescriptor": "COMMON.ACCEPT.INAPP.PAYMENT", "dataValue": "x"},
    "order_id": "order-test-1",
    "customer_email": EMAIL,
    "customer_name": "Jane Doe",
    "state": "VA",
    "county": "Norfolk",
    "property_address": "123 Main St",
    "property_city": "Norfolk",
    "property_zip": "23510",
})
d = resp.json()
check("charge 200 + success", resp.status_code == 200 and d.get("success") is True)
check("needs_verification = True", d.get("needs_verification") is True)

db = SessionLocal()  # pi-lens-ignore: python-sql-injection
case = db.query(Case).filter(Case.email == EMAIL).first()  # pi-lens-ignore: python-sql-injection
user = db.query(User).filter(User.email == EMAIL).first()  # pi-lens-ignore: python-sql-injection
check("Case created", case is not None)
check("Case status = pending_email_verification", case is not None and case.status == "pending_email_verification")
check("Case user_id is NULL", case is not None and case.user_id is None)
check("NO User created before verification", user is None)
check("verification email sent", any("Verify your email" in m for m in captured))
db.close()

# ── 2. Verify email ──────────────────────────────────────────────────────────
print("\n=== 2. Verify email (/verify-email) ===")
db = SessionLocal()  # pi-lens-ignore: python-sql-injection
case = db.query(Case).filter(Case.email == EMAIL).first()  # pi-lens-ignore: python-sql-injection
token = sign_verification_token(EMAIL, str(case.id))
db.close()
resp = client.get(f"/api/v1/auth/verify-email?token={token}")
check("verify returns 200", resp.status_code == 200)

db = SessionLocal()  # pi-lens-ignore: python-sql-injection
user = db.query(User).filter(User.email == EMAIL).first()  # pi-lens-ignore: python-sql-injection
case = db.query(Case).filter(Case.email == EMAIL).first()  # pi-lens-ignore: python-sql-injection
check("User created after verify", user is not None)
check("Case linked to user", user is not None and case is not None and case.user_id == user.id)
check("Case status = intake_in_progress", case is not None and case.status == "intake_in_progress")
check("welcome email sent", any("Your evictions.help account is ready" in m for m in captured))
db.close()

# ── 3. Extract temp password + login ────────────────────────────────────────
print("\n=== 3. Login ===")
temp_pw = None
for m in captured:
    match = re.search(r"Password:\s*(\S+)", m)
    if match:
        temp_pw = match.group(1)
check("temp password found in welcome email", temp_pw is not None)

if temp_pw:
    resp = client.post("/api/v1/auth/login", json={"email": EMAIL, "password": temp_pw})
    check("login 200 with temp password", resp.status_code == 200)
    token = resp.json().get("token") if resp.status_code == 200 else None
    check("login returns a token", bool(token))

    # ── 4. /me ──────────────────────────────────────────────────────────────
    print("\n=== 4. /me (account + case) ===")
    resp = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    me = resp.json()
    check("me 200", resp.status_code == 200)
    check("me returns user email", me.get("user", {}).get("email") == EMAIL)
    check("me returns the case", me.get("case", {}).get("id") == case.id if case else False)
    print("  me response:", {k: (v if k != "id" else v[:8]) for k, v in me.get("case", {}).items()} if me.get("case") else None)

# ── Summary ─────────────────────────────────────────────────────────────────
print("\n" + "=" * 50)
print(f"PASSED: {len(PASS)}  FAILED: {len(FAIL)}")
if FAIL:
    print("FAILED STEPS:")
    for f in FAIL:
        print(f"  - {f}")
    sys.exit(1)
print("🎉 ACCOUNT FLOW VERIFIED")
