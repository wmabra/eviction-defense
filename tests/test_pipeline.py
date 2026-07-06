"""
End-to-end pipeline test — pre-screen through document extraction.
"""
import os
import sys
import json
from pathlib import Path

# Ensure we can import from the project
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_pipeline():
    """Test the complete customer flow end-to-end."""
    # Ensure DB tables exist
    from app.database import init_db
    init_db()

    # Step 1: Pre-screen — eligibility check
    print("=== 1. Pre-screen ===")
    resp = client.post("/api/v1/intake/pre-screen", json={
        "state": "FL",
        "county": "Miami-Dade",
        "is_tenant": True,
        "is_residential": True,
        "received_court_papers": True,
        "has_writ_or_sheriff": False,
        "is_section_8": False,
        "is_active_military": False,
        "has_bankruptcy": False,
        "has_documents_to_upload": True,
    })
    data = resp.json()
    assert data["eligible"] == True
    print(f"  ✅ Eligible: {data['message']}")

    # Step 2: Submit intake (creates case in DB automatically)
    print("=== 2. Submit intake ===")
    resp = client.post("/api/v1/intake/submit?case_id=demo-e2e-001", json={
        "personal_info": {
            "full_name": "Jane Doe",
            "property_address": "123 Main St, Apt 4B",
            "property_city": "Miami",
            "property_zip": "33101",
            "county": "Miami-Dade",
            "phone": "(305) 555-1234",
            "email": "jane@example.com",
        },
        "landlord_info": {
            "landlord_name": "Bayview Apartments LLC",
            "landlord_address": "456 Owner Blvd, Miami, FL 33101",
        },
        "case_details": {
            "case_number": "CACE-24-54321",
            "court_name": "Miami-Dade County",
            "received_3day_notice": True,
            "summons_service_date": "2026-06-28",
            "complaint_amount_claimed": 2850.00,
        },
        "rent_payment": {
            "monthly_rent": 1425.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 1425.00,
            "why_disagree": "I paid half before the notice.",
        },
        "defenses": {
            "def_repairs": {"checked": True, "explanation": "AC broken since May."},
            "def_amount": {"checked": True, "explanation": "Already paid $1,425."},
            "def_bad_notice": {"checked": True, "explanation": "Notice was defective."},
            "def_paid": {"checked": False, "explanation": ""},
            "def_waived": {"checked": False, "explanation": ""},
            "def_retaliation": {"checked": False, "explanation": ""},
            "def_fair_housing": {"checked": False, "explanation": ""},
            "def_accepted_rent": {"checked": False, "explanation": ""},
            "def_corrected": {"checked": False, "explanation": ""},
            "def_not_owner": {"checked": False, "explanation": ""},
            "def_attempted_pay": {"checked": False, "explanation": ""},
            "def_other": {"checked": False, "explanation": ""},
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "hardship_reason": "Lost my job.",
            "wants_payment_plan": True,
            "payment_plan_amount": 500.00,
        },
    })
    assert resp.status_code == 200
    print(f"  ✅ Intake submitted for case: demo-e2e-001")

    # Step 4: Upload a document
    print("=== 4. Upload document ===")
    doc_content = (
        "IN THE COUNTY COURT IN AND FOR MIAMI-DADE COUNTY, FLORIDA\n"
        "CASE NO.: CACE-24-54321\n"
        "BAYVIEW APARTMENTS LLC, Plaintiff,\n"
        "vs.\n"
        "JANE DOE, Defendant.\n"
        "\n"
        "SUMMONS FOR EVICTION\n"
        "Amount claimed: $2,850.00\n"
        "Service date: June 28, 2026\n"
        "You are required to file a written response within 5 days.\n"
    )
    resp = client.post(
        "/api/v1/documents/upload/demo-e2e-001",
        files={"file": ("summons.pdf", doc_content.encode(), "application/pdf")},
        data={"doc_type": "summons"},
    )
    assert resp.status_code == 200
    doc_result = resp.json()
    print(f"  ✅ Uploaded: {doc_result['filename']} (ID: {doc_result['document_id']})")

    # Step 5: Run extraction
    print("=== 5. AI Extraction ===")
    resp = client.post("/api/v1/documents/extract/demo-e2e-001")
    assert resp.status_code == 200
    result = resp.json()
    print(f"  Status: {result['status']}")

    if result.get("extraction"):
        for k, v in result["extraction"].items():
            if v:
                print(f"    {k}: {v}")

    if result.get("has_conflicts"):
        print(f"  ⚠ {len(result['conflicts'])} data conflicts found")

    # Step 6: Check extraction status
    print("=== 6. Status check ===")
    resp = client.get("/api/v1/documents/extraction-status/demo-e2e-001")
    status = resp.json()
    print(f"  Status: {status['status']}")
    print(f"  Documents uploaded: {len(status['documents'])}")
    extracted_keys = list(status.get("extracted_data", {}).keys())
    print(f"  Extracted fields: {extracted_keys}")
    print(f"  Confirmed: {status['extraction_confirmed']}")

    # Step 7: Confirm extraction (simulates customer clicking "confirm")
    print("=== 7. Confirmation ===")
    confirmation_fields = {
        "full_name": {"value": "Jane Doe", "confirmed": True},
        "property_address": {"value": "123 Main St, Apt 4B", "confirmed": True},
        "county": {"value": "Miami-Dade", "confirmed": True},
        "case_number": {"value": "CACE-24-54321", "confirmed": True},
        "landlord_name": {"value": "Bayview Apartments LLC", "confirmed": True},
        "amount_claimed": {"value": "$2,850.00", "confirmed": True},
        "service_date": {"value": "2026-06-28", "confirmed": True},
        "response_deadline": {"value": "2026-07-07", "confirmed": True},
    }
    resp = client.post(
        "/api/v1/documents/confirm/demo-e2e-001",
        json=confirmation_fields,
    )
    confirm_result = resp.json()
    print(f"  Result: {confirm_result['status']}")
    assert confirm_result["status"] == "confirmed"
    print(f"  ✅ {confirm_result['message']}")

    # Step 8: Verify final status
    print("=== 8. Final status ===")
    resp = client.get("/api/v1/intake/status/demo-e2e-001")
    final = resp.json()
    print(f"  Status: {final['status']}")
    print(f"  Extraction confirmed: {final.get('extraction_confirmed')}")
    assert final["status"] == "confirmation_complete"
    print("  ✅ Pipeline complete!")

    print("\n🎉 FULL PIPELINE PASSED")


if __name__ == "__main__":
    test_full_pipeline()
