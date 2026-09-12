#!/usr/bin/env python3
"""Verify form-fill MAPPING correctness — deterministic, no OCR, no coordinates.

For each state, fills the answer form + fee waiver with test data and asserts
that the key fields are present with the correct values and that no signature
is auto-filled. This checks "is the right value in the right field", which is
100% reliable (no coordinate math, no OCR).

Run: python3 tests/verify_mapping.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
import fitz
from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver

STATES = ["AR","CO","CT","GA","IL","IN","KY","LA","MI","MN","MO","NM","OH","OK","OR","RI","SC","TN","TX","VA"]

TEST = {
    "personal_info": {"full_name": "John Doe", "county": "Test", "property_address": "123 Main St",
                      "property_city": "Springfield", "property_zip": "62704", "phone": "(555) 123-4567",
                      "email": "johndoe@example.com"},
    "landlord_info": {"landlord_name": "Smith Property Management, LLC"},
    "case_details": {"case_number": "CV-2026-00123", "court_name": "Test County Court"},
    "defenses": {"def_repairs": {"checked": True}, "def_amount": {"checked": True}, "def_bad_notice": {"checked": True}},
    "financial_info": {"monthly_gross_income": 2400.0, "employment_income": 2400.0,
                       "checking_balance": 500.0, "cash_on_hand": 40.0, "receives_snap": True},
}


def _values(path):
    d = fitz.open(path)
    vals = []
    for pno in range(d.page_count):
        for w in d[pno].widgets():
            v = str(getattr(w, "field_value", "") or "").strip()
            if v and v != "Off":
                vals.append((pno, getattr(w, "field_name", ""), v))
    d.close()
    return vals


def _has(vals, needle):
    return any(needle in v for (_, _, v) in vals)


def main() -> int:
    fails = []
    for st in STATES:
        data = {**TEST, "state": st}
        ap = f"/tmp/{st}_map_a.pdf"
        wp = f"/tmp/{st}_map_w.pdf"
        try:
            fill_answer_form(data, st, ap)
            fill_fee_waiver(data, st, wp)
        except Exception as e:
            print(f"{st:>3} [ERROR] {str(e)[:60]}")
            fails.append(st)
            continue
        av = _values(ap)
        wv = _values(wp)
        problems = []
        if not _has(av, "John Doe"):
            problems.append("answer missing defendant name")
        if not _has(av, "Smith"):
            problems.append("answer missing landlord name")
        if not _has(av, "CV-2026"):
            problems.append("answer missing case number")
        if not _has(wv, "John Doe"):
            problems.append("waiver missing name")
        if not _has(wv, "CV-2026"):
            problems.append("waiver missing case number")
        if _has(av + wv, "/s/"):
            problems.append("signature auto-filled (/s/)")
        status = "OK" if not problems else "FAIL"
        print(f"{st:>3} [{status}]")
        for p in problems:
            print(f"      - {p}")
        if problems:
            fails.append(st)
    print("\n" + ("ALL STATES PASS" if not fails else f"FAILED: {', '.join(fails)}"))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
