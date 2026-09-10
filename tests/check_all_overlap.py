#!/usr/bin/env python3
"""Run the OCR overlap check across all 20 states' answer forms + fee waivers."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

from tests.check_overlap import check_overlap
from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver, _get_form_path
from app.services.state_configs import get_state_config

STATES = ["AR","CO","CT","GA","IL","IN","KY","LA","MI","MN","MO","NM","OH","OK","OR","RI","SC","TN","TX","VA"]

def make_data(state):
    return {
        "state": state,
        "personal_info": {"full_name": "John Doe", "county": "Test", "property_address": "123 Main St",
                          "property_city": "Springfield", "property_zip": "62704", "phone": "(555) 123-4567",
                          "email": "johndoe@example.com"},
        "landlord_info": {"landlord_name": "Smith Property Management, LLC"},
        "case_details": {"case_number": "CV-2026-00123", "court_name": "Test County Court"},
        "defenses": {"def_repairs": {"checked": True}, "def_amount": {"checked": True}, "def_bad_notice": {"checked": True}},
        "financial_info": {"monthly_gross_income": 2400, "employment_income": 2400, "checking_balance": 500,
                           "cash_on_hand": 40, "receives_snap": True},
    }

print(f"{'State':>6} | {'answer form':>12} | {'fee waiver':>10}")
print("-" * 40)
for st in STATES:
    data = make_data(st)
    cfg = get_state_config(st)
    results = []
    # answer form
    ans_filled = f"/tmp/{st}_ans.pdf"
    ans_blank = cfg.get("answer_form")
    if ans_blank:
        try:
            fill_answer_form(data, st, ans_filled)
            blank = os.path.join("app/templates/counties", ans_blank)
            if os.path.exists(blank):
                results.append(f"answer={len(check_overlap(ans_filled, blank))}")
            else:
                results.append("answer=NOFORM")
        except Exception as e:
            results.append(f"answer=ERR({str(e)[:20]})")
    # fee waiver
    fw_filled = f"/tmp/{st}_fw.pdf"
    fw_blank = cfg.get("fee_waiver_form")
    if fw_blank:
        try:
            fill_fee_waiver(data, st, fw_filled)
            blank = os.path.join("app/templates/counties", fw_blank)
            if os.path.exists(blank):
                results.append(f"waiver={len(check_overlap(fw_filled, blank))}")
            else:
                results.append("waiver=NOFORM")
        except Exception as e:
            results.append(f"waiver=ERR({str(e)[:20]})")
    print(f"{st:>6} | {results[0]:>12} | {results[1] if len(results)>1 else '':>10}")
