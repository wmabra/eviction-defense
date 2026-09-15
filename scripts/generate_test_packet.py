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
    "label": "AR",
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
    "label": "CO",
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

CO_DENVER = {
    "full_name": FULL_NAME,
    "county": "Denver",
    "label": "CO_Denver",
    "data": {
        "state": "CO",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(720) 555-0149",
            "email": "john.doe.denver@example.com",
            "property_address": "1450 S Pearl Street",
            "property_city": "Denver",
            "property_zip": "80210",
            "county": "Denver",
        },
        "landlord_info": {
            "landlord_name": "Mile High Property Group, LLC",
            "landlord_address": "1745 Larimer Street, Denver, CO 80202",
            "landlord_phone": "(720) 555-0114",
            "landlord_email": "leasing@milehighpg.example",
        },
        "case_details": {
            "case_number": "2024CV12345",
            "court_name": "Denver County Court",
            "complaint_amount_claimed": 2600.00,
            "summons_service_date": "2024-05-20",
            "response_deadline": "2024-05-27",
            "court_date": "2024-06-05",
        },
        "rent_payment": {
            "monthly_rent": 1300.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 1040.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The heating system has been broken since January and the "
                               "landlord has refused to repair it despite multiple written requests.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes a charge for a month I already paid and "
                               "unauthorized pet fees.",
            },
            "def_retaliation": {
                "checked": True,
                "explanation": "The landlord filed this eviction after I reported the broken "
                               "heater to the Denver Department of Public Health.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I was laid off in March and have been covering rent from "
                               "savings while I look for work.",
            "needs_continuance": True,
            "continuance_reason": "I need time to obtain bank statements and the city "
                                  "inspection report for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I need time to secure a new rental while my rental "
                                     "assistance application is pending.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-13579-EEB",
            "bankruptcy_court": "U.S. Bankruptcy Court, District of Colorado",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-05-24",
            "bankruptcy_attorney_name": "Susan Advocate, Esq.",
            "bankruptcy_attorney_phone": "(720) 555-0177",
            "bankruptcy_attorney_email": "sadvocate@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 3200.00,
            "employment_income": 3200.00,
            "unemployment_income": 0.00,
            "rent_or_mortgage": 1300.00,
            "utilities_expense": 260.00,
            "food_expense": 520.00,
            "transportation_expense": 200.00,
            "medical_expense": 150.00,
            "child_care_expense": 400.00,
            "total_monthly_expenses": 2830.00,
            "cash_on_hand": 200.00,
            "checking_balance": 100.00,
            "savings_balance": 50.00,
            "vehicle_make_model": "2016 Toyota Corolla",
            "vehicle_value": 7500.00,
            "vehicle_loan_owed": 3000.00,
            "owns_real_estate": False,
            "household_adults": 2,
            "household_children": 2,
            "receives_public_benefits": True,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}

# ── Fake John Doe — Connecticut (Hartford Judicial District) ──────────────
CT = {
    "full_name": FULL_NAME,
    "county": "Hartford",
    "label": "CT",
    "data": {
        "state": "CT",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(860) 555-0171",
            "email": "john.doe.ct@example.com",
            "property_address": "238 Maple Avenue",
            "property_city": "Hartford",
            "property_zip": "06112",
            "county": "Hartford",
        },
        "landlord_info": {
            "landlord_name": "Nutmeg State Properties, LLC",
            "landlord_address": "100 Constitution Plaza, Hartford, CT 06103",
            "landlord_phone": "(860) 555-0118",
            "landlord_email": "leasing@nutmegstate.example",
        },
        "case_details": {
            "case_number": "HFH-CV24-6012345",
            "court_name": "Hartford Housing Court",
            "complaint_amount_claimed": 2400.00,
            "summons_service_date": "2024-05-15",
            "response_deadline": "2024-05-22",
            "court_date": "2024-05-29",
        },
        "rent_payment": {
            "monthly_rent": 1200.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 960.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The heating system has been broken since January and the landlord has not repaired it despite written notice.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes unauthorized late fees and charges a month I already paid.",
            },
            "def_paid": {
                "checked": True,
                "explanation": "I paid rent in full for the months claimed except for one disputed balance.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I lost my job in February and have been covering rent from savings while seeking new work.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to obtain bank statements and repair receipts for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I need time to secure rental assistance and avoid displacement while my application is pending.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-20678",
            "bankruptcy_court": "U.S. Bankruptcy Court, District of Connecticut",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-05-10",
            "bankruptcy_attorney_name": "Maria Advocate, Esq.",
            "bankruptcy_attorney_phone": "(860) 555-0133",
            "bankruptcy_attorney_email": "madvocate@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 2800.00,
            "monthly_net_income": 2200.00,
            "employment_income": 2800.00,
            "rent_or_mortgage": 1200.00,
            "utilities_expense": 200.00,
            "food_expense": 420.00,
            "transportation_expense": 160.00,
            "medical_expense": 100.00,
            "child_care_expense": 0.00,
            "debt_payments": 250.00,
            "total_monthly_expenses": 2330.00,
            "cash_on_hand": 100.00,
            "checking_balance": 200.00,
            "savings_balance": 50.00,
            "vehicle_value": 6000.00,
            "vehicle_loan_owed": 2500.00,
            "household_adults": 2,
            "household_children": 1,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}


# ── Fake John Doe — Georgia (Fulton County / Atlanta) ────────────────────
GA = {
    "full_name": FULL_NAME,
    "county": "Fulton",
    "label": "GA",
    "data": {
        "state": "GA",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(404) 555-0167",
            "email": "john.doe.ga@example.com",
            "property_address": "857 Peachtree Street NE",
            "property_city": "Atlanta",
            "property_zip": "30309",
            "county": "Fulton",
        },
        "landlord_info": {
            "landlord_name": "Peach State Properties, LLC",
            "landlord_address": "3344 Piedmont Road NE, Atlanta, GA 30305",
            "landlord_phone": "(404) 555-0119",
            "landlord_email": "leasing@peachstate.example",
        },
        "case_details": {
            "case_number": "24D0012345",
            "court_name": "Magistrate Court of Fulton County",
            "complaint_amount_claimed": 2600.00,
            "summons_service_date": "2024-05-10",
            "response_deadline": "2024-05-17",
            "court_date": "2024-05-24",
        },
        "rent_payment": {
            "monthly_rent": 1300.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 1040.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The air conditioning and plumbing have been broken since March and the landlord has not repaired them despite written requests.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes late fees that are not allowed and charges a month I already paid.",
            },
            "def_bad_notice": {
                "checked": True,
                "explanation": "I did not receive a proper written demand for possession before the dispossessory was filed.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I was laid off in February and have been covering rent from savings while looking for work.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to obtain repair receipts and bank statements for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I need time to secure rental assistance and avoid displacement while my application is pending.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-53412-pmb",
            "bankruptcy_court": "U.S. Bankruptcy Court, Northern District of Georgia",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-05-06",
            "bankruptcy_attorney_name": "David Counsel, Esq.",
            "bankruptcy_attorney_phone": "(404) 555-0128",
            "bankruptcy_attorney_email": "dcounsel@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 2200.00,
            "employment_income": 2200.00,
            "rent_or_mortgage": 1300.00,
            "utilities_expense": 190.00,
            "food_expense": 410.00,
            "transportation_expense": 170.00,
            "medical_expense": 90.00,
            "debt_payments": 200.00,
            "total_monthly_expenses": 2360.00,
            "cash_on_hand": 80.00,
            "checking_balance": 120.00,
            "savings_balance": 40.00,
            "vehicle_make_model": "2014 Nissan Altima",
            "vehicle_value": 5200.00,
            "owns_real_estate": False,
            "household_adults": 2,
            "household_children": 1,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}


# ── Fake John Doe — Illinois (Cook County / Chicago) ───────────────────
IL = {
    "full_name": FULL_NAME,
    "county": "Cook",
    "label": "IL",
    "data": {
        "state": "IL",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(312) 555-0163",
            "email": "john.doe.il@example.com",
            "property_address": "4823 S Kedzie Avenue",
            "property_city": "Chicago",
            "property_zip": "60632",
            "county": "Cook",
        },
        "landlord_info": {
            "landlord_name": "Windy City Property Management, LLC",
            "landlord_address": "200 W Madison Street, Chicago, IL 60606",
            "landlord_phone": "(312) 555-0117",
            "landlord_email": "leasing@windycitypm.example",
        },
        "case_details": {
            "case_number": "2024M1123456",
            "court_name": "Circuit Court of Cook County",
            "complaint_amount_claimed": 2400.00,
            "summons_service_date": "2024-05-02",
            "response_deadline": "2024-05-12",
            "court_date": "2024-05-15",
        },
        "rent_payment": {
            "monthly_rent": 1200.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 960.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The heat and hot water have been intermittent since January and the landlord has not repaired them despite written requests.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes unauthorized late fees and charges a month I already paid.",
            },
            "def_bad_notice": {
                "checked": True,
                "explanation": "I did not receive a proper written notice before the eviction was filed.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I was laid off in February and have been covering rent from savings while looking for work.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to obtain repair receipts and bank statements for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I need time to secure rental assistance and avoid displacement while my application is pending.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-09876",
            "bankruptcy_court": "U.S. Bankruptcy Court, Northern District of Illinois",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-04-28",
            "bankruptcy_attorney_name": "Laura Advocate, Esq.",
            "bankruptcy_attorney_phone": "(312) 555-0121",
            "bankruptcy_attorney_email": "ladvocate@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 2000.00,
            "employment_income": 2000.00,
            "social_security_income": 0.00,
            "child_support_income": 0.00,
            "unemployment_income": 0.00,
            "pension_income": 0.00,
            "rent_or_mortgage": 1200.00,
            "utilities_expense": 180.00,
            "food_expense": 380.00,
            "medical_expense": 110.00,
            "child_care_expense": 0.00,
            "cash_on_hand": 60.00,
            "vehicle_value": 4800.00,
            "household_adults": 1,
            "household_children": 1,
            "receives_snap": True,
            "receives_ssi": False,
            "receives_tanf": False,
            "receives_county_assistance": False,
        },
    },
}


# ── Fake John Doe — Indiana (Marion County / Indianapolis) ───────────────
IN = {
    "full_name": FULL_NAME,
    "county": "Marion",
    "label": "IN",
    "data": {
        "state": "IN",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(317) 555-0145",
            "email": "john.doe.in@example.com",
            "property_address": "3125 E Washington Street",
            "property_city": "Indianapolis",
            "property_zip": "46201",
            "county": "Marion",
        },
        "landlord_info": {
            "landlord_name": "Circle City Rentals, LLC",
            "landlord_address": "1 N Meridian Street, Indianapolis, IN 46204",
            "landlord_phone": "(317) 555-0113",
            "landlord_email": "leasing@circlecityrentals.example",
        },
        "case_details": {
            "case_number": "49D01-2405-SC-012345",
            "court_name": "Marion County Small Claims Court",
            "complaint_amount_claimed": 2200.00,
            "summons_service_date": "2024-04-22",
            "response_deadline": "2024-05-05",
            "court_date": "2024-05-08",
        },
        "rent_payment": {
            "monthly_rent": 1100.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 880.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The furnace and water heater have been broken since February and the landlord has not repaired them despite written requests.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes unauthorized late fees and charges a month I already paid.",
            },
            "def_bad_notice": {
                "checked": True,
                "explanation": "I did not receive proper written notice before the eviction was filed.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I was laid off in February and have been covering rent from savings while looking for work.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to obtain repair receipts and bank statements for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I need time to secure rental assistance and avoid displacement while my application is pending.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-04567-jmc",
            "bankruptcy_court": "U.S. Bankruptcy Court, Southern District of Indiana",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-04-18",
            "bankruptcy_attorney_name": "Mark Counsel, Esq.",
            "bankruptcy_attorney_phone": "(317) 555-0124",
            "bankruptcy_attorney_email": "mcounsel@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 2100.00,
            "employment_income": 2100.00,
            "unemployment_income": 0.00,
            "ssi_income": 0.00,
            "child_support_income": 0.00,
            "rent_or_mortgage": 1100.00,
            "utilities_expense": 170.00,
            "food_expense": 360.00,
            "child_care_expense": 0.00,
            "medical_expense": 95.00,
            "transportation_expense": 150.00,
            "other_expenses": 60.00,
            "total_monthly_expenses": 1935.00,
            "household_adults": 1,
            "household_children": 2,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}


# ── Fake John Doe — Kentucky (Jefferson County / Louisville) ─────────────
KY = {
    "full_name": FULL_NAME,
    "county": "Jefferson",
    "label": "KY",
    "data": {
        "state": "KY",
        "personal_info": {
            "full_name": FULL_NAME,
            "phone": "(502) 555-0143",
            "email": "john.doe.ky@example.com",
            "property_address": "1523 W Broadway",
            "property_city": "Louisville",
            "property_zip": "40203",
            "county": "Jefferson",
        },
        "landlord_info": {
            "landlord_name": "Bluegrass Property Group, LLC",
            "landlord_address": "400 W Market Street, Louisville, KY 40202",
            "landlord_phone": "(502) 555-0115",
            "landlord_email": "leasing@bluegrasspg.example",
        },
        "case_details": {
            "case_number": "24-F-012345",
            "court_name": "Jefferson District Court",
            "complaint_amount_claimed": 1900.00,
            "summons_service_date": "2024-04-15",
            "response_deadline": "2024-04-25",
            "court_date": "2024-04-28",
        },
        "rent_payment": {
            "monthly_rent": 950.00,
            "agree_with_amount": False,
            "amount_tenant_believes_owed": 760.00,
        },
        "defenses": {
            "def_repairs": {
                "checked": True,
                "explanation": "The furnace has been broken since January and the landlord has not repaired it despite written requests.",
            },
            "def_amount": {
                "checked": True,
                "explanation": "The ledger includes unauthorized late fees and charges a month I already paid.",
            },
            "def_bad_notice": {
                "checked": True,
                "explanation": "I did not receive proper written notice before the forcible detainer was filed.",
            },
        },
        "preferences": {
            "trial_by": "judge",
            "needs_more_time": True,
            "wants_payment_plan": True,
            "hardship_reason": "I was laid off in January and have been covering rent from savings while looking for work.",
            "needs_continuance": True,
            "continuance_reason": "I need additional time to obtain repair receipts and bank statements for the hearing.",
            "needs_emergency_stay": True,
            "emergency_stay_reason": "I need time to secure rental assistance and avoid displacement while my application is pending.",
            "facing_writ_possession": True,
            "filing_bankruptcy": True,
            "bankruptcy_case_number": "24-31012-tnw",
            "bankruptcy_court": "U.S. Bankruptcy Court, Western District of Kentucky",
            "bankruptcy_chapter": "7",
            "bankruptcy_filing_date": "2024-04-10",
            "bankruptcy_attorney_name": "Sarah Advocate, Esq.",
            "bankruptcy_attorney_phone": "(502) 555-0122",
            "bankruptcy_attorney_email": "sadvocate@example.com",
        },
        "financial_info": {
            "monthly_gross_income": 1900.00,
            "employment_income": 1900.00,
            "social_security_income": 0.00,
            "unemployment_income": 0.00,
            "pension_income": 0.00,
            "child_support_income": 0.00,
            "alimony_income": 0.00,
            "rent_or_mortgage": 950.00,
            "utilities_expense": 160.00,
            "food_expense": 340.00,
            "transportation_expense": 140.00,
            "medical_expense": 85.00,
            "total_monthly_expenses": 1675.00,
            "cash_on_hand": 50.00,
            "household_adults": 1,
            "household_children": 2,
            "receives_snap": True,
            "receives_medicaid": True,
            "receives_ssi": False,
            "receives_tanf": False,
        },
    },
}


PACKETS = {"AR": AR, "CO": CO, "CO_DENVER": CO_DENVER, "CT": CT, "GA": GA, "IL": IL, "IN": IN, "KY": KY}


def main() -> int:
    state = (sys.argv[1] if len(sys.argv) > 1 else "AR").upper()
    if state not in PACKETS:
        print(f"Unknown state {state!r}. Choose from {sorted(PACKETS)}.", file=sys.stderr)
        return 2

    pkg = PACKETS[state]
    full_name = pkg["full_name"]
    data = pkg["data"]

    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    pkg_name = f"{pkg.get('label', state)}_{full_name.replace(' ', '_')}"
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
