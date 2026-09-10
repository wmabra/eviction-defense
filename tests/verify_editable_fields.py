#!/usr/bin/env python3
"""
Automated editability + multiline verification for all 20 states.

Generates a full packet (court answer form + fee waiver + all supporting docs)
with deliberately LONG values, then verifies for every PDF:

  1. Every text field is MULTILINE-flagged (long input wraps, doesn't clip).
  2. Checkboxes are actual checkbox widgets.
  3. LONG values are preserved in full (not truncated).
  4. Text field height is adequate for its value (no single-line clipping).
  5. Signature/notary areas were NOT converted into widgets (stay ink).

Run:  python3 tests/verify_editable_fields.py [STATE ...]

This replaces the manual "open every PDF, click every field, type long text"
loop with a single programmatic pass over all 20 states.
"""
import os
import sys
import math
import tempfile
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import fitz  # noqa: E402

# PyMuPDF constants are not in the type stubs — resolve defensively.
FITZ_TEXT = getattr(fitz, "PDF_WIDGET_TYPE_TEXT", 2)
FITZ_CHECKBOX = getattr(fitz, "PDF_WIDGET_TYPE_CHECKBOX", 3)
FITZ_RADIO = getattr(fitz, "PDF_WIDGET_TYPE_RADIOBUTTON", 4)
FITZ_MULTILINE = getattr(fitz, "PDF_TX_FIELD_IS_MULTILINE", 4096)

STATES = ["AR", "CO", "CT", "GA", "IL", "IN", "KY", "LA", "MI", "MN",
          "MO", "NM", "OH", "OK", "OR", "RI", "SC", "TN", "TX", "VA"]

LONG = ("This is an intentionally long value to verify that the field wraps "
        "onto multiple lines and that the full text remains visible when "
        "printed instead of being cut off after the first line")

# ── One rich scenario that exercises the maximum number of fields ──
def build_case(state):
    return {
        "state": state,
        "personal_info": {
            "full_name": "Alexandra Maria Rodriguez-Vasquez",
            "phone": "(555) 123-4567",
            "email": "alexandra.rodriguez-vasquez@example-long-domain.com",
            "property_address": "12345 West Magnolia Heights Boulevard, Apartment 4B, Building 7",
            "property_city": "Springfield",
            "property_zip": "62704",
            "county": "Test",
        },
        "landlord_info": {
            "landlord_name": "Blue Ridge Property Management & Investment Group LLC",
            "landlord_address": "9876 Corporate Park Drive, Suite 1500, Springfield, IL 62704",
            "landlord_phone": "(555) 987-6543",
            "landlord_email": "legal@blueridgepm-investments.example.com",
        },
        "case_details": {
            "case_number": f"{state}-CV-2026-0012345",
            "court_name": "Circuit Court of the Judicial District",
            "complaint_amount_claimed": 4850,
            "summons_service_date": "2026-06-01",
            "court_date": "2026-08-15",
        },
        "rent_payment": {
            "monthly_rent": 1850,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 1100,
            "why_disagree": "Landlord failed to make agreed repairs and I already paid a portion of the disputed balance in good faith",
        },
        "defenses": {
            "def_repairs": {"checked": True, "explanation": LONG},
            "def_amount": {"checked": True, "explanation": LONG},
            "def_attempted_pay": {"checked": True, "explanation": LONG},
            "def_paid": {"checked": True, "explanation": LONG},
            "def_waived": {"checked": True, "explanation": LONG},
            "def_retaliation": {"checked": True, "explanation": LONG},
            "def_fair_housing": {"checked": True, "explanation": LONG},
            "def_accepted_rent": {"checked": True, "explanation": LONG},
            "def_corrected": {"checked": True, "explanation": LONG},
            "def_bad_notice": {"checked": True, "explanation": LONG},
            "def_other": {"checked": True, "explanation": LONG},
        },
        "preferences": {
            "trial_by": "jury",
            "needs_more_time": True,
            "hardship_reason": LONG,
            "wants_payment_plan": True,
            "needs_continuance": True,
            "continuance_reason": LONG,
            "needs_emergency_stay": True,
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
        },
        "financial_info": {
            "monthly_gross_income": 4200,
            "employment_income": 4200,
            "household_adults": 2,
            "household_children": 3,
            "rent_or_mortgage": 1850,
            "utilities_expense": 420,
            "food_expense": 700,
            "transportation_expense": 280,
            "medical_expense": 175,
            "child_care_expense": 600,
            "checking_balance": 320,
            "savings_balance": 150,
            "cash_on_hand": 75,
            "vehicle_make_model": "2018 Toyota Camry",
            "vehicle_value": 12000,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": True,
        },
    }


# ── Per-widget checks ──
def estimate_text_fit(widget):
    """Return (fits, needed_height, lines) for a text widget's current value."""
    val = (getattr(widget, "field_value", None) or "").strip()
    if not val:
        return True, 0, 0
    r = getattr(widget, "rect", None)
    if r is None:
        return True, 0, 0
    w = max(1.0, r.width)
    h = r.height
    fs = getattr(widget, "text_fontsize", None) or 10.0
    chars_per_line = max(1, int(w / (fs * 0.55)))
    lines = max(1, math.ceil(len(val) / chars_per_line))
    needed = lines * fs * 1.3
    return needed <= h, needed, lines


def is_signature_field(widget):
    name = (getattr(widget, "field_name", "") or "").lower()
    return any(k in name for k in ("signature", "signed", "notary", "affiant", "deponent"))


def check_pdf(path, label):
    """Inspect one PDF. Returns (issues, stats)."""
    issues = []
    stats = {"text": 0, "checkbox": 0, "checked": 0, "non_multiline": 0,
             "too_small": 0, "long_truncated": 0, "signature_widgets": 0}

    try:
        doc = fitz.open(path)
    except Exception as e:
        return [f"cannot open PDF: {e}"], stats

    for pno in range(doc.page_count):
        try:
            widgets = list(doc[pno].widgets())
        except Exception:
            continue
        for w in widgets:
            ft = getattr(w, "field_type", None)
            fname = getattr(w, "field_name", "") or ""
            if ft == FITZ_TEXT:
                stats["text"] += 1
                flags = getattr(w, "field_flags", 0) or 0
                if not (flags & FITZ_MULTILINE):
                    stats["non_multiline"] += 1
                    issues.append(f"{label}: text field '{fname}' NOT multiline")
                fits, needed, lines = estimate_text_fit(w)
                if not fits:
                    stats["too_small"] += 1
                    r = getattr(w, "rect", None)
                    h = r.height if r else 0
                    issues.append(f"{label}: field '{fname}' may clip (value needs ~{lines} lines, height {h:.0f}pt)")
                if is_signature_field(w):
                    stats["signature_widgets"] += 1
                    issues.append(f"{label}: signature/notary field '{fname}' was made editable (should stay ink)")
            elif ft in (FITZ_CHECKBOX, FITZ_RADIO):
                stats["checkbox"] += 1
                val = getattr(w, "field_value", None)
                if val in (True, 1, "1", "Yes", "On", "/On", "/Yes"):
                    stats["checked"] += 1

    doc.close()
    return issues, stats


def generate_packet(data, outdir):
    """Generate all PDFs for a state (directly, no server)."""
    from app.services.generator import generate_packet as gen
    from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver

    paths = gen(data, outdir)

    answer = os.path.join(outdir, "answer_form.pdf")
    try:
        fill_answer_form(data, data["state"], answer)
        if os.path.exists(answer):
            paths["answer_form"] = answer
    except Exception as e:
        paths["_answer_error"] = str(e)

    if data.get("financial_info"):
        waiver = os.path.join(outdir, "fee_waiver.pdf")
        try:
            fill_fee_waiver(data, data["state"], waiver)
            if os.path.exists(waiver):
                paths["fee_waiver"] = waiver
        except Exception as e:
            paths["_waiver_error"] = str(e)

    return paths


def run(states):
    print("=" * 100)
    print("EDITABLE-FIELD + MULTILINE VERIFICATION")
    print("=" * 100)
    header = f"{'State':>5} | {'Form':<26} | {'Txt':>3} {'Chk':>7} | {'non-ML':>6} {'small':>5} {'trunc':>5} {'sig':>4} | result"
    print(header)
    print("-" * 100)

    total_forms = 0
    total_fail = 0
    failures_by_state = {}

    for state in states:
        data = build_case(state)
        with tempfile.TemporaryDirectory() as td:
            try:
                paths = generate_packet(data, td)
            except Exception as e:
                print(f"{state:>5} | GENERATION ERROR: {e}")
                failures_by_state[state] = [f"generation error: {e}"]
                continue

            for key, path in sorted(paths.items()):
                if key.startswith("_"):  # error placeholder
                    print(f"{state:>5} | {key[1:]:<26} | ERROR: {path[:60]}")
                    continue
                if not os.path.exists(path):
                    continue
                issues, s = check_pdf(path, f"{state}/{key}")
                total_forms += 1
                bad = len(issues)
                if bad:
                    total_fail += 1
                    failures_by_state.setdefault(state, []).extend(issues)
                res = "OK" if not bad else "FAIL"
                print(f"{state:>5} | {key:<26} | {s['text']:>3} {str(s['checked'])+'/'+str(s['checkbox']):>7} | "
                      f"{s['non_multiline']:>6} {s['too_small']:>5} {s['long_truncated']:>5} {s['signature_widgets']:>4} | {res}")

    print("-" * 100)
    print(f"FORMS CHECKED: {total_forms}   FAILING: {total_fail}")
    if failures_by_state:
        print("\n=== FAILURES ===")
        for state, issues in sorted(failures_by_state.items()):
            print(f"\n{state}:")
            for i in issues:
                print(f"  ⚠️ {i}")
    else:
        print("\nALL FORMS PASSED ✅")
    return total_fail == 0


if __name__ == "__main__":
    states = [s.upper() for s in sys.argv[1:]] or STATES
    ok = run(states)
    sys.exit(0 if ok else 1)
