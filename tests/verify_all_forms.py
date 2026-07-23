"""
Automated Form Verification Suite — tests all 20 states across 4 scenarios.
Run: python3 tests/verify_all_forms.py
"""
import urllib.request, json, io, zipfile, fitz, os, sys, traceback
from datetime import datetime

BASE = "http://localhost:8000"
STATES = ['AR','AZ','CA','CO','CT','FL','GA','IL','LA','MA','MI','MN','NM','NV','OR','RI','SC','TN','TX','VA']

# ═══════════════════════════════════════════════════════════
# TEST SCENARIOS — 4 realistic user profiles
# ═══════════════════════════════════════════════════════════

SCENARIO_1 = {
    "name": "Full Defenses + Financial Hardship",
    "description": "Tenant has multiple defenses, needs more time, wants payment plan, receives benefits",
    "personal_info": {"full_name": "Scenario One", "phone": "555-000-1111", "email": "s1@test.com",
        "property_address": "100 Main St", "property_city": "Testville", "property_zip": "11111", "county": "Test"},
    "landlord_info": {"landlord_name": "Landlord One LLC"},
    "case_details": {"case_number": "S1-2024-001", "court_name": "Test County Court", "complaint_amount_claimed": 3500, "summons_service_date": "2026-06-01"},
    "rent_payment": {"monthly_rent": 1800, "agree_with_amount": False, "amount_tenant_believes_owed": 1200, "why_disagree": "Already paid $600"},
    "defenses": {
        "def_repairs": {"checked": True, "explanation": "Broken AC since April, mold in bathroom"},
        "def_amount": {"checked": True, "explanation": "Only owe $1200, paid $600 already"},
        "def_attempted_pay": {"checked": True, "explanation": "Offered to pay full amount on June 1"},
        "def_retaliation": {"checked": True, "explanation": "Filed after I reported code violations"},
        "def_bad_notice": {"checked": True, "explanation": "Notice had wrong dates"},
        "def_other": {"checked": True, "explanation": "Landlord entered without notice multiple times"},
    },
    "preferences": {"trial_by": "judge", "needs_more_time": True, "hardship_reason": "Medical recovery from surgery", "wants_payment_plan": True},
    "financial_info": {"monthly_gross_income": 2800, "employment_income": 2800, "household_adults": 2, "household_children": 2,
        "rent_or_mortgage": 1800, "utilities_expense": 350, "food_expense": 600, "transportation_expense": 200,
        "medical_expense": 300, "checking_balance": 150, "cash_on_hand": 50, "vehicle_make_model": "2018 Toyota Camry",
        "vehicle_value": 12000, "receives_snap": True, "receives_medicaid": True, "receives_public_benefits": True},
}

SCENARIO_2 = {
    "name": "Minimal Defenses + No Financials",
    "description": "Tenant has one defense, no financial data, no extra requests",
    "personal_info": {"full_name": "Scenario Two", "phone": "555-000-2222", "email": "s2@test.com",
        "property_address": "200 Oak Ave", "property_city": "Testville", "property_zip": "22222", "county": "Test"},
    "landlord_info": {"landlord_name": "Landlord Two Inc"},
    "case_details": {"case_number": "S2-2024-001", "court_name": "Test County Court", "complaint_amount_claimed": 2200},
    "rent_payment": {"monthly_rent": 1200, "agree_with_amount": True},
    "defenses": {"def_repairs": {"checked": True, "explanation": "No heat in winter"}},
    "preferences": {"trial_by": "judge"},
    "financial_info": None,
}

SCENARIO_3 = {
    "name": "Pre-Eviction + Payment Dispute",
    "description": "Tenant not served yet, disputes amount, has hearing date",
    "personal_info": {"full_name": "Scenario Three", "phone": "555-000-3333", "email": "s3@test.com",
        "property_address": "300 Pine Rd Apt 7", "property_city": "Testville", "property_zip": "33333", "county": "Test"},
    "landlord_info": {"landlord_name": "Landlord Three Properties", "landlord_address": "500 Business Pkwy"},
    "case_details": {"case_number": "S3-2024-001", "court_name": "Test County Court", "complaint_amount_claimed": 5000,
        "court_date": "2026-08-15", "summons_service_date": "2026-07-01"},
    "rent_payment": {"monthly_rent": 2500, "agree_with_amount": False, "amount_tenant_believes_owed": 2000, "why_disagree": "Rent increase was illegal"},
    "defenses": {"def_amount": {"checked": True, "explanation": "Illegal rent increase without proper notice"},
        "def_bad_notice": {"checked": True, "explanation": "Notice to quit was defective"}},
    "preferences": {"trial_by": "jury", "needs_continuance": True, "continuance_reason": "Need time to gather evidence"},
    "financial_info": {"monthly_gross_income": 5000, "employment_income": 5000, "household_adults": 1, "household_children": 0,
        "rent_or_mortgage": 2500, "checking_balance": 3000, "savings_balance": 5000},
}

SCENARIO_4 = {
    "name": "All Defenses + Bankruptcy Adjacent + Emergency",
    "description": "Complex case: all 12 defenses, facing writ, emergency motion needed",
    "personal_info": {"full_name": "Scenario Four", "phone": "555-000-4444", "email": "s4@test.com",
        "property_address": "400 Elm Street", "property_city": "Testville", "property_zip": "44444", "county": "Test"},
    "landlord_info": {"landlord_name": "Landlord Four Holdings LLC"},
    "case_details": {"case_number": "S4-2024-001", "court_name": "Test County Court", "complaint_amount_claimed": 8000,
        "summons_service_date": "2026-05-15"},
    "rent_payment": {"monthly_rent": 3200, "agree_with_amount": False, "amount_tenant_believes_owed": 0, "why_disagree": "Unit was uninhabitable"},
    "defenses": {
        "def_repairs": {"checked": True, "explanation": "No running water for 3 weeks"},
        "def_amount": {"checked": True, "explanation": "Unit uninhabitable — rent not owed"},
        "def_attempted_pay": {"checked": True, "explanation": "Offered partial payment for habitable portion"},
        "def_paid": {"checked": True, "explanation": "Paid for hotel while unit uninhabitable"},
        "def_waived": {"checked": True, "explanation": "Landlord said I could stay if I fixed things myself"},
        "def_retaliation": {"checked": True, "explanation": "Retaliation for health department complaint"},
        "def_fair_housing": {"checked": True, "explanation": "Discrimination based on family status"},
        "def_accepted_rent": {"checked": True, "explanation": "Landlord accepted partial payment after notice"},
        "def_corrected": {"checked": True, "explanation": "Fixed the plumbing issue myself"},
        "def_not_owner": {"checked": False},
        "def_bad_notice": {"checked": True, "explanation": "Notice was not properly served"},
        "def_other": {"checked": True, "explanation": "Landlord harassing and threatening me"},
    },
    "preferences": {"trial_by": "jury", "needs_more_time": True, "hardship_reason": "Finding new housing",
        "wants_payment_plan": True, "needs_emergency_stay": True, "facing_writ_possession": True,
        "needs_continuance": True, "continuance_reason": "Need to gather witness statements"},
    "financial_info": {"monthly_gross_income": 4200, "employment_income": 4200, "household_adults": 1, "household_children": 3,
        "rent_or_mortgage": 3200, "utilities_expense": 400, "food_expense": 800, "transportation_expense": 300,
        "medical_expense": 150, "child_care_expense": 600, "checking_balance": 500, "cash_on_hand": 100,
        "vehicle_make_model": "2015 Honda Odyssey", "vehicle_value": 8000, "receives_snap": True, "receives_ssi": True},
}

SCENARIOS = [SCENARIO_1, SCENARIO_2, SCENARIO_3, SCENARIO_4]

# ═══════════════════════════════════════════════════════════
# FIELD VALIDATION RULES
# ═══════════════════════════════════════════════════════════

# Fields that SHOULD always be filled on the answer form
ANSWER_REQUIRED_FIELDS = [
    "defendant_name", "plaintiff_name", "case_number", "county", "date",
]

# Fields that may or may not be filled depending on scenario
ANSWER_CONDITIONAL = [
    "court_name", "property_address", "phone", "email", "printed_name", "signature",
]

# Fields that are OK to be blank (attorney fields, witness info, etc.)
ANSWER_OPTIONAL = [
    "attorney", "bar", "witness", "courtroom", "division", "cos", "mailing",
    "language", "translator", "interpreter", "jury", "counterclaim", "crossclaim",
]

# Fee waiver fields that should be filled when financial_info is present
FEE_REQUIRED_WITH_FINANCIALS = [
    "name", "case", "county", "income", "rent",
]


def generate_packet(state, scenario):
    """Generate a packet for a state+scenario combination."""
    body = json.loads(json.dumps(scenario))
    body["state"] = state
    body["case_details"]["case_number"] = f"{state}-{scenario['case_details']['case_number']}"
    body["personal_info"]["county"] = "Test"
    
    data = json.dumps(body).encode()
    req = urllib.request.Request(f"{BASE}/api/v1/documents/generate-packet",
        data=data, headers={"Content-Type": "application/json"})
    r = urllib.request.urlopen(req, timeout=30)
    return zipfile.ZipFile(io.BytesIO(r.read()))


def audit_form(zip_file, form_pattern, required_checks, scenario):
    """Audit a court form or fee waiver — returns list of issues."""
    matches = [n for n in zip_file.namelist() if form_pattern in n]
    if not matches:
        return [f"MISSING: {form_pattern}"], {}
    
    zip_file.extract(matches[0], "/tmp/")
    doc = fitz.open(f"/tmp/{matches[0]}")
    
    # Collect all widget data
    widgets = {}
    for i in range(doc.page_count):
        for w in list(doc[i].widgets()):
            widgets[w.field_name] = str(w.field_value) if w.field_value else ""
    
    # Collect all page text
    all_text = ""
    for i in range(doc.page_count):
        all_text += doc[i].get_text()
    
    doc.close()
    os.unlink(f"/tmp/{matches[0]}")
    
    # Run checks
    issues = []
    p = scenario.get("personal_info", {})
    l = scenario.get("landlord_info", {})
    c = scenario.get("case_details", {})
    fin = scenario.get("financial_info") or {}
    defenses = scenario.get("defenses", {})
    prefs = scenario.get("preferences", {})
    full_name = p.get("full_name", "")
    landlord_name = l.get("landlord_name", "")
    case_number = c.get("case_number", "")
    state_code = scenario.get("state", "")
    
    # Check 1: Core identity fields
    name_found = landlord_found = case_found = False
    for field_name, value in widgets.items():
        fn = field_name.lower()
        val = value.lower()
        if full_name.lower() in val or (fn and "defendant" in fn and full_name.lower() in val):
            name_found = True
        if landlord_name.lower() in val or (fn and "plaintiff" in fn and landlord_name.lower() in val):
            landlord_found = True
        if case_number in value:
            case_found = True
    
    if not name_found and full_name not in all_text:
        issues.append("DEFENDANT NAME MISSING")
    if not landlord_found and landlord_name not in all_text:
        issues.append("PLAINTIFF NAME MISSING")
    if not case_found and case_number not in all_text:
        issues.append("CASE NUMBER MISSING")
    
    # Check 2: Defense checkboxes
    if form_pattern == "COURT_FORM_Answer":
        checked_defenses = [k for k, v in defenses.items() if isinstance(v, dict) and v.get("checked")]
        defense_matches = 0
        defense_off = 0
        
        for field_name, value in widgets.items():
            fn = field_name.lower()
            if any(kw in fn for kw in ["defense", "repair", "amount", "paid", "retaliat", "notice", "waive"]):
                if value.lower() == "yes" or value == "1":
                    defense_matches += 1
                elif value.lower() == "off" or value == "":
                    defense_off += 1
        
        # If no widget-based defenses found, check for narrative
        narrative_text = ""
        for field_name, value in widgets.items():
            if "narrative" in field_name.lower() and len(value) > 10:
                narrative_text = value
                break
        
        if defense_matches == 0 and not narrative_text and checked_defenses:
            issues.append(f"NO DEFENSES FILLED (expected {len(checked_defenses)}: {checked_defenses})")
    
    # Check 3: Fee waiver specific
    if form_pattern == "Fee_Waiver":
        has_any_income = False
        has_any_benefits = False
        has_any_assets = False
        
        for field_name, value in widgets.items():
            val = value.strip()
            if val and val != "Off" and val != "0":
                fn = field_name.lower()
                if any(kw in fn for kw in ["income", "8a", "8b", "8c", "8d", "9a"]):
                    has_any_income = True
                if any(kw in fn for kw in ["snap", "medicaid", "ssi", "tanf", "6.1", "6.2", "6.3", "6.4", "6.5"]):
                    if val.lower() == "yes":
                        has_any_benefits = True
                if any(kw in fn for kw in ["vehicle", "10b", "checking", "savings", "cash"]):
                    has_any_assets = True
        
        if fin and not has_any_income:
            issues.append("FEE WAIVER: NO INCOME DATA (financial_info provided)")
        if fin.get("receives_snap") or fin.get("receives_medicaid"):
            if not has_any_benefits:
                issues.append("FEE WAIVER: BENEFITS CHECKBOXES NOT CHECKED")
        if fin.get("vehicle_make_model") or fin.get("checking_balance"):
            if not has_any_assets:
                issues.append("FEE WAIVER: ASSETS NOT FILLED")
    
    # Check 4: Blank widgets that should be filled
    blank_count = 0
    for field_name, value in widgets.items():
        fn = field_name.lower()
        val = value.strip()
        if not val or val == "Off":
            # Skip known optional fields
            if any(opt in fn for opt in ANSWER_OPTIONAL):
                continue
            blank_count += 1
    
    details = {
        "total_widgets": len(widgets),
        "filled_widgets": sum(1 for v in widgets.values() if v.strip() and v != "Off"),
        "blank_important": blank_count,
        "name_ok": name_found,
        "landlord_ok": landlord_found,
        "case_ok": case_found,
    }
    
    return issues, details


def run_all_tests():
    """Run all 80 tests (20 states × 4 scenarios) and print report."""
    print("=" * 80)
    print(f"FORM VERIFICATION SUITE — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 80)
    
    total_tests = 0
    total_pass = 0
    all_issues = {}
    
    for scenario in SCENARIOS:
        print(f"\n{'─' * 80}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"  {scenario['description']}")
        print(f"{'─' * 80}")
        print(f"{'State':>5} {'Answer':>8} {'Fee Wvr':>8} {'Docs':>5} {'Issues'}")
        print("-" * 75)
        
        for state in STATES:
            total_tests += 1
            try:
                z = generate_packet(state, scenario)
                doc_count = len(z.namelist())
                
                # Audit answer form
                answer_issues, answer_details = audit_form(z, "COURT_FORM_Answer", [], scenario)
                
                # Audit fee waiver (only if financial_info present)
                fw_issues = []
                fw_details = {}
                if scenario.get("financial_info"):
                    fw_issues, fw_details = audit_form(z, "Fee_Waiver", [], scenario)
                else:
                    fw_details = {"filled_widgets": "N/A"}
                
                all_bad = answer_issues + fw_issues
                passed = len(all_bad) == 0
                
                if passed:
                    total_pass += 1
                    print(f"  {state:>2}  {'✅':>8} {'✅' if not fw_issues else '✅':>8} {doc_count:>4}  PASS")
                else:
                    key = f"{scenario['name']} / {state}"
                    all_issues[key] = all_bad
                    summary = "; ".join(all_bad[:3])
                    if len(all_bad) > 3:
                        summary += f" (+{len(all_bad)-3} more)"
                    print(f"  {state:>2}  {'❌' if answer_issues else '✅':>8} {'❌' if fw_issues else '✅':>8} {doc_count:>4}  {summary}")
                    
            except Exception as e:
                print(f"  {state:>2}  {'ERROR':>8}  {str(e)[:50]}")
    
    # Summary
    print(f"\n{'=' * 80}")
    print(f"RESULTS: {total_pass}/{total_tests} passed")
    
    if all_issues:
        print(f"\nISSUES FOUND ({len(all_issues)} state/scenario combinations):")
        for key, issues in sorted(all_issues.items()):
            print(f"  {key}:")
            for issue in issues:
                print(f"    ⚠️ {issue}")
    
    print(f"\n{'=' * 80}")
    if total_pass == total_tests:
        print("ALL TESTS PASSED ✅")
    else:
        print(f"FAILED: {total_tests - total_pass} tests need fixes")
    
    return total_pass == total_tests


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
