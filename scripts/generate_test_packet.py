"""
Generate a full eviction-defense test packet for a single fake user.

Usage:
    venv/bin/python scripts/generate_test_packet.py [AR|CO]

Builds a complete packet (supporting docs + filled court answer form +
fee waiver) from the per-state test data below, writes the unpacked files to
test_packages/<STATE>_<full_name>/ and zips them to
test_packages/<STATE>_<full_name>_packet.zip.

Mirrors the logic in app/routers/documents.py::_build_and_return_packet so the
output is identical to what the admin generate-test-packet endpoint produces.
"""
import os
import sys
import zipfile
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from app.services.generator import generate_packet
from app.services.form_filler import fill_answer_form
from app.services.pdf_overlay import fill_fee_waiver

logging.basicConfig(level=logging.WARNING)

FULL_NAME = "John Doe"

# ── Fake John Doe — Arkansas (Pulaski County / Little Rock) ────────────────
AR = {
    "full_name": FULL_NAME,
    "county": "Pulaski",
    "data": {
        "state": "AR",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(501) 555-0147",
            "email": "john.doe@example.com",
            "property_address": "742 Elm Street",
            "property_city": "Little Rock",
            "property_zip": "72204",
            "county": "Pulaski",
        },
        "landlord_info": {
            "landlord_name": "Oak Ridge Properties, LLC",
            "landlord_address": "1200 Chenal Parkway, Little Rock, AR 72211",
            "landlord_phone": "(501) 555-0199",
            "landlord_email": "leasing@oakridge-properties.example",
        },
        "case_details": {
            "case_number": "CV-24-01847",
            "court_name": "Pulaski County District Court",
            "complaint_amount_claimed": 1850.00,
            "summons_service_date": "2024-06-03",
            "response_deadline": "2024-06-10",
            "court_date": "2024-06-20",
        },
        "rent_payment": {
            "monthly_rent": 925.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 740.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The heating and plumbing have been broken since March "
                               "and the landlord failed to make repairs despite written notice.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The landlord's ledger includes late fees that are not allowed "
                               "and double-charges a month I already paid.",
            },
            "def_bad_notice": {
                "checked": True,
                "explanation": "I did not receive the required 14-day notice to quit before "
                               "the complaint was filed.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I lost my job in April and am actively looking for new "
                               "employment while caring for my two children.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to secure legal representation "
                                  "and gather documents for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I am facing imminent eviction and need time to arrange "
                                     "rental assistance and alternative housing.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "4:24-bk-11234",
            "bankruptcy_court": "U.S. Bankruptcy Court, Eastern District of Arkansas",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-06-08",
            "bankruptcy_attorney_name": "Jane Counsel, Esq.",
            "bankruptcy_attorney_phone": "(501) 555-0111",
            "bankruptcy_attorney_email": "jcounsel@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 1800.00,
            "employment_income": 0.00,
            "unemployment_income": 1800.00,
            "rent_or_mortgage": 925.00,
            "utilities_expense": 180.00,
            "food_expense": 400.00,
            "household_adults": 1,
            "household_children": 2,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}

# ── Fake John Doe — Colorado (Jefferson County / Lakewood) ─────────────────
CO = {
    "full_name": FULL_NAME,
    "county": "Jefferson",
    "data": {
        "state": "CO",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(303) 555-0173",
            "email": "john.doe.303@example.com",
            "property_address": "4812 W Cedar Avenue",
            "property_city": "Lakewood",
            "property_zip": "80226",
            "county": "Jefferson",
        },
        "landlord_info": {
            "landlord_name": "Summit Ridge Property Management, LLC",
            "landlord_address": "950 Wadsworth Boulevard, Lakewood, CO 80214",
            "landlord_phone": "(303) 555-0119",
            "landlord_email": "leasing@summitridgepm.example",
        },
        "case_details": {
            "case_number": "2024C030123",
            "court_name": "Jefferson County Court",
            "complaint_amount_claimed": 2200.00,
            "summons_service_date": "2024-05-28",
            "response_deadline": "2024-06-04",
            "court_date": "2024-06-12",
        },
        "rent_payment": {
            "monthly_rent": 1100.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 880.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The furnace and refrigerator have been broken since February "
                               "and the landlord has not made repairs despite written requests.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes unauthorized late fees and a charge for a "
                               "month I already paid in full.",
            },
            "def_retaliation": {
                "checked": True,
                "explanation": "The landlord filed this eviction after I complained to the "
                               "Jefferson County housing authority about the lack of heat.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I had to take unpaid medical leave in April and fell behind "
                               "while recovering and returning to work.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to gather pay stubs, bank records, "
                                  "and the housing authority inspection report.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I am awaiting a decision on a rental assistance "
                                     "application and need time to avoid displacement.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-11234-MER",
            "bankruptcy_court": "U.S. Bankruptcy Court, District of Colorado",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-06-03",
            "bankruptcy_attorney_name": "Robert Counsel, Esq.",
            "bankruptcy_attorney_phone": "(303) 555-0123",
            "bankruptcy_attorney_email": "rcounsel@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 2400.00,
            "employment_income": 2400.00,
            "unemployment_income": 0.00,
            "rent_or_mortgage": 1100.00,
            "utilities_expense": 210.00,
            "food_expense": 450.00,
            "transportation_expense": 180.00,
            "medical_expense": 120.00,
            "child_care_expense": 300.00,
            "total_monthly_expenses": 2360.00,
            "cash_on_hand": 150.00,
            "checking_balance": 75.00,
            "savings_balance": 0.00,
            "vehicle_make_model": "2012 Honda Civic",
            "vehicle_value": 4500.00,
            "vehicle_loan_owed": 0.00,
            "owns_real_estate": False,
            "household_adults": 2,
            "household_children": 1,
            "receives_public_benefits": True,
            "receives_snap": True,
            "receives_medicaid": False,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}

PACKETS = {"AR": AR, "CO": CO}


def main() -> int:
    state = (sys.argv[1] if len(sys.argv) > 1 else "AR").upper()
    if state not in PACKETS:
        print(f"Unknown state {state!r}. Choose from {sorted(PACKETS)}.", file=sys.stderr)
        return 2

    pkg = PACKETS[state]
    full_name = pkg["full_name"]
    data = pkg["data"]

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg_name = f"{state}_{full_name.replace(' ', '_')}"
    out_dir = os.path.join(base_dir, "test_packages", pkg_name)
    try:
        os.makedirs(out_dir, exist_ok=True)
    except OSError as e:
        print(f"Could not create output dir {out_dir}: {e}", file=sys.stderr)
        return 1

    # 1. Supporting documents
    paths = generate_packet(data, out_dir)

    # 2. Official court answer form
    state_code = data.get("state", state).upper()
    court_pdf = os.path.join(out_dir, "01_COURT_FORM_Answer_FILE_THIS.pdf")
    fill_answer_form(data, state_code, court_pdf)
    paths["court_form"] = court_pdf

    # 3. Fee waiver (tenant has financial info)
    fee_waiver_pdf = os.path.join(out_dir, "02_COURT_FORM_Fee_Waiver_FILE_THIS.pdf")
    fill_fee_waiver(data, state_code, fee_waiver_pdf)
    paths["fee_waiver"] = fee_waiver_pdf

    # 4. Zip everything
    zip_path = os.path.join(base_dir, "test_packages", f"{pkg_name}_packet.zip")
    with zipfile.ZipFile(zip_path, "w") as zf:
        for name, filepath in sorted(paths.items()):
            if os.path.exists(filepath):
                zf.write(filepath, os.path.basename(filepath))

    print(f"Generated {len(paths)} files -> {out_dir}")
    for name, filepath in sorted(paths.items()):
        size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
        print(f"  {os.path.basename(filepath):45s} {size:>8,} bytes")
    print(f"\nZip: {zip_path} ({os.path.getsize(zip_path):,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
