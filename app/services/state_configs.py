"""
Per-state form configuration — field mappings, defense options, court info.

Each state config maps our generic data fields to that state PDF's field names.
This is the bridge between the intake data and the court forms.
"""

from typing import Dict, List, Optional

# ──────────────────────────────────────────────
# Common data keys we collect (same for all states)
# ──────────────────────────────────────────────
# personal_info: full_name, phone, email, property_address, property_city,
#                property_zip, county, co_tenants
# landlord_info: landlord_name, landlord_address, landlord_phone, landlord_email
# case_details: case_number, court_name, notice_amount_demanded, etc.
# rent_payment: monthly_rent, agree_with_amount, amount_tenant_believes_owed
# defenses: { checked, explanation } per defense key

StateConfig = dict


def get_state_config(state_code: str) -> Optional[StateConfig]:
    """Get the configuration for a given state (returns None if not configured)."""
    return STATE_CONFIGS.get(state_code.upper())


STATE_CONFIGS: Dict[str, StateConfig] = {
    # ══════════════════════════════════════════
    # VIRGINIA — DC-442 Grounds of Defense
    # 26 fillable fields
    # ══════════════════════════════════════════
    "VA": {
        "name": "Virginia",
        "answer_form": "va_eviction_answer.pdf",
        "fee_waiver_form": "va_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "User.PetitionerResidenceAddress",
            "bank_accounts": "User.BankAccounts",
            "case_number": "User.CaseNo",
            "cash_on_hand": "User.CashOnHand",
            "child_care_expense": "User.ChildCarePayments",
            "county": "User.CityOrCounty",
            "court_name": "User.CourtName",
            "date": "User.DateSigned",
            "email": "User.PetitionerEmail",
            "full_name": "User.Name1",
            "household_size": "User.NoInHousehold",
            "medical_expense": "User.MedicalExp",
            "phone": "User.PetitionerTelephone",
            "printed_name": "User.PrintNamePetitioner",
            "receives_public_benefits": "User.CB02",
            "receives_snap": "User.CB06",
            "receives_ssi": "User.CB05",
            "receives_tanf": "User.CB03",
        },
        "has_fillable_fields": True,
        "court_type": "General District Court",
        "field_mapping": {
            "full_name": "User.Defendant",
            "phone": "User.PhoneName2",
            "address": "User.AddressName2",
            "landlord_name": "User.Plaintiff",
            "case_number": "User.CaseNo",
            "court_name": "User.Court",
            "date": "User.Date3",
            "day": "User.Day",
            "month": "User.Month",
            "year": "User.Year",
        },
        "defense_options": [
            {"key": "def_not_owed", "label": "I do not owe the amount claimed", "field": "User.CB1"},
            {"key": "def_landlord_breach", "label": "The landlord breached the rental agreement", "field": "User.CB1"},
            {"key": "def_repairs", "label": "Landlord failed to maintain premises", "field": "User.CB1"},
            {"key": "def_retaliation", "label": "The eviction is in retaliation", "field": "User.CB1"},
            {"key": "def_discrimination", "label": "The eviction is discriminatory", "field": "User.CB1"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice", "field": "User.CB1"},
        ],
        "notes": "DC-442 Grounds of Defense — 26 fillable fields. Used in General District Court for unlawful detainer cases.",
        "fee_waiver_mapping": {
            "case_number": "User.CaseNo",
            "court_name": "User.CourtName",
            "full_name": "User.Name1",
            "county": "User.CityOrCounty",
            "date": "User.DateSigned",
            "printed_name": "User.PrintNamePetitioner",
            "address": "User.PetitionerResidenceAddress",
            "phone": "User.PetitionerTelephone",
            "email": "User.PetitionerEmail",
        },
    },

    # ══════════════════════════════════════════
    # SOUTH CAROLINA — SCCA703 Answer
    # 22 fillable fields (descriptive names)
    # ══════════════════════════════════════════
    "SC": {
        "name": "South Carolina",
        "answer_form": "sc_eviction_answer.pdf",
        "fee_waiver_form": "sc_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "case_number": "File Numnber",
            "cash_on_hand": "Fill in Cash Amount",
            "checking_balance": "Fill in Money in Bank Amount",
            "child_care_expense": "Fill in Child Care Amount",
            "child_support_income": "Fill in Alimony  Child Support Amount",
            "county": "Select the County",
            "date": "Enter Day of Sworn",
            "debt_payments": "Fill in Car Payment Amount",
            "employment_income": "Fill in Earnings Amount",
            "food_expense": "Fill in Food Amount",
            "full_name": "Name",
            "household_adults": "Fill in Number of Adult Dependents Residing in the Home",
            "household_children": "Fill in Number of Minor Dependents Residing in the Home",
            "medical_expense": "Fill in Medical  Dental  Vision Amount",
            "rent_or_mortgage": "Fill in Rent  Mortgage Amount",
            "social_security_income": "Fill in Social Security VA Benefits, Workers' Comp or Disability Amount",
            "total_monthly_expenses": "Fill in Total Amounts (Add Lines 1-14)",
            "transportation_expense": "Fill in Car Expenses Amount",
            "unemployment_income": "Fill in Unemployment Amount",
            "utilities_expense": "Fill in Utilities Amount",
        },
        "has_fillable_fields": True,
        "court_type": "Magistrates Court",
        "field_mapping": {
            "full_name": "Defendant(s) Name",
            "phone": "Defendant(s) Telephone Number",
            "email": "Defendant(s) Email Address",
            "address": "Defendant(s) Street Address",
            "city_state_zip": "City, State and Zip Code of the Defendant(s) Street Address",
            "landlord_name": "Plaintiff Name",
            "landlord_address": "Plaintiff Street Address",
            "landlord_city_state_zip": "City, State and Zip Code of the Plaintiff\u2019s Street Address",
            "landlord_phone": "Plaintiff\u2019s Telephone Number",
            "case_number": "Civil Case Number",
            "county": "County of:",
            "court_name": "Magistrate Court Filed With",
            "date_served": "Date Served with a Complaint",
        },
        "defense_options": [
            {"key": "def_admit_all", "label": "I admit everything in the complaint and do not want a trial", "field": "I admit everything in the complaint and do not want a trial"},
            {"key": "def_admit_partial", "label": "I am responsible but not for the total amount", "field": "I admit that I am responsible, but not for the total amount claimed by the Plaintiff(s)"},
            {"key": "def_contest", "label": "I contest the jurisdiction of the court", "field": "I contest the jurisdiction of the court"},
            {"key": "def_deny_all", "label": "I deny that I am responsible at all", "field": "I deny that I am responsible at all"},
        ],
        "field_mapping_defense_explanation": {
            "contest_reason": "Reason of Contestation, Use Additional Pages if Necessary",
            "deny_reason": "Reason Not Responsible at All For Amount Claimed, Use Additional Pages if Necessary",
            "partial_reason": "Reason Not Responsible for Total Amount Claimed, Use Additional Pages if Necessary",
        },
    },

    # ══════════════════════════════════════════
    # GEORGIA — MAG-30-02 Dispossessory Answer
    # 44 fillable fields
    # ══════════════════════════════════════════
    "GA": {
        "name": "Georgia",
        "answer_form": "ga_eviction_answer.pdf",
        "fee_waiver_form": "ga_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "2 Current Address",
            "case_number": "FILE NO",
            "checking_balance": "What is the current balance in your account",
            "debt_payments": "Total_2",
            "email": "4 Email Address",
            "employment_income": "TOTAL AMOUNT OF INCOME RECEIVED PER MONTH IF ANY",
            "full_name": "1 Name",
            "household_children": "2 How many people not including yourself do you currently support",
            "phone": "3 Best Telephone Number to Reach You",
            "real_estate_loan_owed": "How much do you owe on the property mortgage balance",
            "real_estate_value": "What is the approximate value of the property",
            "savings_balance": "What is the current balance in your account_2",
            "total_monthly_expenses": "Total_3",
            "vehicle_make_model": "Make",
            "vehicle_value": "What is the approximate value of the vehicle",
        },
        "has_fillable_fields": True,
        "court_type": "Magistrate Court",
        "field_mapping": {
            "case_number": "CaseNumber",
            "county": "County.Selection",
            "date": "Date.CurrentDate.SlashMDY",
            "full_name": "Defendant.SEQ001.Name.Full",
            "address": "Defendant.SEQ001.HomeAddress.Street",
            "landlord_name": "Plaintiff.SEQ001.Name.Full",
            "landlord_address": "Plaintiff.SEQ001.HomeAddress.Street",
            "plaintiff_city_state": "Plaintiff.SEQ001.HomeAddress.CityStateZip",
        },
        "defense_options": [
            {"key": "def_did_repairs", "label": "Defendant did make repairs", "field": "DidMakeRepairs"},
            {"key": "def_failed_repair", "label": "Landlord failed to repair", "field": "FailedToRepair"},
            {"key": "def_no_notice", "label": "No notice given", "field": "NoNotice"},
            {"key": "def_no_rent_due", "label": "No rent is due", "field": "NoRentDue"},
            {"key": "def_offered_pay", "label": "Offered to pay", "field": "OfferedToPay"},
            {"key": "def_refused_payment", "label": "Landlord refused payment", "field": "LandlordRefusePayment"},
            {"key": "def_invalid", "label": "Invalid eviction", "field": "Invalid"},
            {"key": "def_retaliation", "label": "Retaliation", "field": "NoLTRel"},
            {"key": "def_landlord_not_entitled", "label": "Landlord not entitled", "field": "LandlordNotEntitled"},
        ],
        "answer_field": "Answer",
        "counterclaim_field": "CounterClaim",
        "did_cause_damages": "DidCauseDamages",
        "does_owe_money": "DoesOweMoney",
    },

    # ══════════════════════════════════════════
    # TEXAS — Eviction Answer (JP Court)
    # 57 fillable fields across 3 pages (generic Text# field names)
    # ══════════════════════════════════════════
    "TX": {
        "name": "Texas",
        "answer_form": "tx_eviction_answer.pdf",
        "fee_waiver_form": "tx_fee_waiver.pdf",
        "overlay_positions": {
            "financial_summary": {"page": 1, "x": 50, "y": 50, "w": 500, "h": 200, "size": 9},
        
            "date": {"page": 1, "x": 129, "y": 54, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 1, "x": 31, "y": 321, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 31, "y": 339, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 1, "x": 31, "y": 422, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 67, "y": 516, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 1, "x": 67, "y": 376, "w": 14, "h": 14, "size": 10},
            "printed_name": {"page": 1, "x": 443, "y": 623, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 443, "y": 623, "w": 200, "h": 20, "size": 10},
            "date": {"page": 2, "x": 151, "y": 176, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 2, "x": 71, "y": 514, "w": 14, "h": 14, "size": 10},
            "email": {"page": 2, "x": 197, "y": 126, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 1, "x": 197, "y": 551, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 3, "x": 415, "y": 353, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 3, "x": 177, "y": 353, "w": 200, "h": 20, "size": 10},
            "court_name": {"page": 1, "x": 478, "y": 114, "w": 200, "h": 16, "size": 10},
            "date": {"page": 3, "x": 584, "y": 346, "w": 120, "h": 16, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 72, "y": 459, "w": 14, "h": 14, "size": 10},
            "defense_bad_notice": {"page": 2, "x": 72, "y": 73, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 1, "x": 108, "y": 597, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 2, "x": 54, "y": 244, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 90, "y": 419, "w": 14, "h": 14, "size": 10},
            "email": {"page": 3, "x": 192, "y": 75, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 3, "x": 372, "y": 419, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 3, "x": 352, "y": 365, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 3, "x": 352, "y": 346, "w": 200, "h": 20, "size": 10},
            "court_name": {"page": 1, "x": 159, "y": 74, "w": 200, "h": 16, "size": 10},
            "date": {"page": 1, "x": 461, "y": 170, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 1, "x": 39, "y": 215, "w": 14, "h": 14, "size": 10},
            "phone": {"page": 1, "x": 350, "y": 678, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 1, "x": 386, "y": 656, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 330, "y": 678, "w": 200, "h": 20, "size": 10}},
        "has_fillable_fields": True,
        "court_type": "Justice of the Peace Court",
        "field_mapping": {
            "case_number": "Text1",
            "full_name": "Text5",
            "landlord_name": "Text2",
            "court_name": "Other Court",
            "phone": "Text8",
            "date": "Text9",
            "email": "Text277",
            "address": "Text18",
            "county": "Text3",
            "printed_name": "Text16",
            "signature_date": "D signature date",
        },
        "defense_options": [
            {"key": "def_paid", "label": "I paid all rent owed", "field": "Check Box6"},
            {"key": "def_repairs", "label": "Landlord failed to maintain/repair premises", "field": "Check Box7"},
            {"key": "def_retaliation", "label": "Retaliatory eviction", "field": "Check Box9"},
            {"key": "def_bad_notice", "label": "Improper notice or no notice", "field": "Check Box10"},
            {"key": "def_amount", "label": "Amount claimed is incorrect", "field": "Check Box54"},
            {"key": "def_moved_out", "label": "I no longer live at the property", "field": "Check Box Does Not Live"},
            {"key": "def_failure_mitigate", "label": "Landlord failed to mitigate damages", "field": "Check Box Mitigate"},
            {"key": "def_discrimination", "label": "Fair Housing Act / discrimination", "field": "Check BoxFHAM"},
            {"key": "def_counterclaim", "label": "Counterclaim against landlord", "field": "Check BoxCD"},
            {"key": "def_other", "label": "Other defenses (Check Box2)", "field": "Check Box2"},
            {"key": "def_other2", "label": "Other defenses (Check Box4)", "field": "Check Box4"},
        ],
        "notes": "TX JP Court eviction answer. 57 fillable fields across 3 pages. Defense checkboxes mapped: Box6=paid, Box7=repairs, Box9=retaliation, Box10=notice, Box54=amount dispute, DoesNotLive=moved out, Mitigate=failure to mitigate, FHAM=discrimination, CD=counterclaim. Box2 and Box4 are catch-all other defenses.",
    
        "fee_waiver_overlay": {
            "address": {"page": 1, "x": 120, "y": 160, "w": 350, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 350, "y": 80, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 120, "y": 100, "w": 200, "h": 20, "size": 11},
            "full_name": {"page": 1, "x": 120, "y": 120, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 1, "x": 120, "y": 180, "w": 200, "h": 20, "size": 11}
        }},

    # ══════════════════════════════════════════
    # ILLINOIS — Statewide eviction answer
    # 156 fillable fields (complex, multi-page)
    # ══════════════════════════════════════════
    "IL": {
        "name": "Illinois",
        "answer_form": "il_eviction_answer.pdf",
        "fee_waiver_form": "il_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "1c - Street Address",
            "case_number": "Trial Court Case Number",
            "cash_on_hand": "4e - Total Value - Bank account & cash",
            "child_care_expense": "4d8 - Childcare Expenses",
            "child_support_income": "4b4 - Child Support Income",
            "county": "County1",
            "date": "Last - Signature",
            "email": "Last - Email",
            "employment_income": "4b2 - My employment income",
            "food_expense": "4d5 - Food Expenses",
            "full_name": "1a - Full Name",
            "household_adults": "2a - Number of Adults",
            "household_children": "2b - Children Under 18",
            "medical_expense": "4d6 - Medical Expenses",
            "pension_income": "4b6 - Pension Income",
            "phone": "Last - Telephone",
            "printed_name": "Last - Print Name",
            "receives_county_assistance": "3E - GA Checkbox",
            "receives_snap": "3B - SNAP Checkbox",
            "receives_ssi": "3a - SSI Checkbox",
            "receives_tanf": "3D - TANF Checkbox",
            "rent_or_mortgage": "4d1 - Monthly Rent Expenses",
            "social_security_income": "4b3 - Social Security - Not SSI",
            "unemployment_income": "4b5 - Unemployment Income",
            "utilities_expense": "4d4 - Utililty Expenses",
            "vehicle_value": "4e - Total Value - 1st Vehicle",
        },
        "has_fillable_fields": True,
        "court_type": "Circuit Court",
        "field_mapping": {
            "county": "1 - County",
            "full_name": "5 - Defendants (First, middle, last name)",
            "landlord_name": "2 - Plaintiff Name (First, Middle, Last)",
            "case_number": "9 - Case Number",
            "property_address": "10 - Property Address",
        },
        "defense_options": [
            # IL uses paragraph admit/deny/do-not-know triads.
            # When tenant has any defense, DENY all complaint paragraphs.
            {"key": "def_repairs", "label": "Deny complaint paragraphs (all)", "field": "14 - Admit/Deny/Do Not Know"},
            # Set second widget of each triad = Deny
            {"key": "def_retaliation", "label": "", "field": "17 - Admit/Deny/Do Not Know"},
            {"key": "def_bad_notice", "label": "", "field": "20 - Admit/Deny/Do Not Know"},
            {"key": "def_amount", "label": "", "field": "23 - Admit/Deny/Do Not Know"},
            {"key": "def_paid", "label": "", "field": "26 - Admit/Deny/Do Not Know"},
            {"key": "def_waived", "label": "", "field": "29 - Admit/Deny/Do Not Know"},
            {"key": "def_accepted_rent", "label": "", "field": "32 - Admit/Deny/Do Not Know"},
            {"key": "def_discrimination", "label": "", "field": "35 - Admit/Deny/Do Not Know"},
            {"key": "def_other", "label": "", "field": "38 - Admit/Deny/Do Not Know"},
            {"key": "def_other", "label": "", "field": "41 - Admit/Deny/Do Not Know"},
            # Specific defense checkboxes (pages 2-3)
            {"key": "def_repairs", "label": "Conditions/repairs defense", "field": "43 - Checkbox"},
            {"key": "def_retaliation", "label": "Retaliation lockout defense", "field": "44 - Checkbox"},
            {"key": "def_bad_notice", "label": "Improper notice defense", "field": "45 - Checkbox"},
            {"key": "def_discrimination", "label": "Fair housing defense", "field": "46 - Checkbox"},
            {"key": "def_other", "label": "Other defense", "field": "52 - Checkbox"},
        ],
        "notes": "IL Circuit Court eviction answer. 189 field widgets across 6 pages. Uses paragraph admit/deny triads mapped to common defenses (any checked defense → Deny that paragraph). Plus specific numbered defense checkboxes mapped on pages 2-3.",
    },

    # ══════════════════════════════════════════
    # CONNECTICUT — JD-HM-5 Summary Process Answer
    # 1 page, 62 fillable fields (defense/specialized fields only)
    # No defendant name field — uses overlay for tenant data
    # ══════════════════════════════════════════
    "CT": {
        "name": "Connecticut",
        "answer_form": "ct_eviction_answer.pdf",
        "fee_waiver_form": "ct_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "topmostSubform[0].Page1[0].ADDRAPP[0]",
            "case_number": "DOCKETNO[0]",
            "cash_on_hand": "CASH",
            "checking_balance": "CHECKING",
            "child_care_expense": "ME6",
            "date": "topmostSubform[0].Page2[0].DATESIGN[0]",
            "debt_payments": "DEBTPAYTOTAL",
            "food_expense": "ME3",
            "full_name": "topmostSubform[0].Page1[0].NAMEAPP[0]",
            "household_children": "DEPENDENTS",
            "medical_expense": "ME5",
            "monthly_gross_income": "GMI",
            "monthly_net_income": "NMI",
            "other_assets_value": "OPPEV",
            "other_income_description": "INCOMEOTHER",
            "phone": "topmostSubform[0].Page1[0].PHONE[0]",
            "printed_name": "topmostSubform[0].Page2[0].NAMESIGN[0]",
            "real_estate_loan_owed": "RELOANBAL",
            "real_estate_value": "REEV",
            "rent_or_mortgage": "ME1",
            "savings_balance": "SAVINGS",
            "total_monthly_expenses": "TOTALME",
            "transportation_expense": "ME4",
            "utilities_expense": "ME2",
            "vehicle_loan_owed": "MVLOANBAL",
            "vehicle_value": "MVEV",
        },
        "has_fillable_fields": True,
        "court_type": "Housing Court / Superior Court",
        "field_mapping": {
            "landlord_name": "LANDLORD[0]",
            "landlord_address": "LANDLORD[1]",
            "case_number": "DOCKETNO[0]",
            "status": "STATUS[0]",
            "additional_info": "ADDINFO[0]",
            "additional_reasons": "ADDITIONALREASONS[0]",
            "cert_address": "CERTADDR[0]",
            "cert_date_signed": "CERTDATESIGN[0]",
            "cert_date": "CERTDATE[0]",
            "cert_mail": "CERTMAIL[0]",
            "cert_name": "CERTNAME[0]",
            "cert_phone": "CERTPHONE[0]",
            "code_violation": "CODEVIOLA[0]",
            "date_increase": "DATEINCREASE[0]",
            "date_note": "DATENOTE[0]",
            "date_offered": "DATEOFFERED[0]",
            "eviction_type": "EVICTION[0]",
            "foreclosure": "FORECLOSE[0]",
            "lease": "LEASE[0]",
            "lease_renewal": "LEASE[1]",
            "no_rent_due": "NORENTDUE[0]",
            "note": "NOTE[0]",
            "notified": "NOTIFIED[0]",
            "pre_termination": "PRETERMINATION[0]",
            "rent_accepted": "RENTACCEPTED[0]",
            "rent_increase": "RENTINCREA[0]",
            "rent_offered": "RENTOFFERED[0]",
            "rent_paid": "RENTPAID[0]",
        },
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 200, "w": 250, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 72, "y": 175, "w": 250, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 425, "y": 93, "w": 130, "h": 20, "size": 10},
            "address": {"page": 1, "x": 72, "y": 220, "w": 300, "h": 20, "size": 10},
            "phone": {"page": 1, "x": 72, "y": 240, "w": 200, "h": 20, "size": 10},
        
            "court_name": {"page": 1, "x": 546, "y": 46, "w": 200, "h": 16, "size": 10},
            "date": {"page": 1, "x": 144, "y": 299, "w": 120, "h": 16, "size": 10},
            "defense_accepted_rent": {"page": 1, "x": 45, "y": 225, "w": 14, "h": 14, "size": 10},
            "defense_amount": {"page": 1, "x": 97, "y": 129, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 45, "y": 213, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 1, "x": 45, "y": 453, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 1, "x": 45, "y": 465, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 1, "x": 45, "y": 225, "w": 14, "h": 14, "size": 10},
            "printed_name": {"page": 1, "x": 128, "y": 659, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 128, "y": 659, "w": 200, "h": 20, "size": 10},
            "date": {"page": 2, "x": 119, "y": 681, "w": 120, "h": 16, "size": 10},
            "defense_accepted_rent": {"page": 3, "x": 164, "y": 476, "w": 14, "h": 14, "size": 10},
            "defense_amount": {"page": 1, "x": 21, "y": 621, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 3, "x": 21, "y": 543, "w": 14, "h": 14, "size": 10},
            "defense_bad_notice": {"page": 2, "x": 130, "y": 220, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 2, "x": 165, "y": 433, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 2, "x": 196, "y": 167, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 2, "x": 185, "y": 718, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 3, "x": 21, "y": 65, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 3, "x": 129, "y": 423, "w": 14, "h": 14, "size": 10},
            "email": {"page": 4, "x": 160, "y": 635, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 4, "x": 159, "y": 67, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 4, "x": 257, "y": 469, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 2, "x": 283, "y": 406, "w": 200, "h": 20, "size": 10}},
        "defense_options": [
            {"key": "def_paid", "label": "I paid the rent", "field": "form1[0].FRONT[0].RENTPAID[0]"},
            {"key": "def_attempted_pay", "label": "I offered to pay but landlord refused", "field": "form1[0].FRONT[0].RENTOFFERED[0]"},
            {"key": "def_accepted_rent", "label": "Landlord accepted rent after notice", "field": "form1[0].FRONT[0].RENTACCEPTED[0]"},
            {"key": "def_not_owed", "label": "I do not owe the rent claimed", "field": "form1[0].FRONT[0].NORENTDUE[0]"},
            {"key": "def_repairs", "label": "Landlord failed to fix conditions / I notified them", "field": "form1[0].FRONT[0].NOTIFIED[0]"},
            {"key": "def_foreclosure", "label": "Property in foreclosure", "field": "form1[0].FRONT[0].FORECLOSE[0]"},
            {"key": "def_pre_termination", "label": "Pre-termination mediation required", "field": "form1[0].FRONT[0].PRETERMINATION[0]"},
        ],
        "notes": "CT JD-HM-5 form — 62 fillable fields but NO defendant name/address field (form assumes case caption provides it). Tenant data (name, address, phone) uses overlay positions. Landlord info, docket number, and defense checkboxes use fillable fields (full XFA dotted paths).",
    },

    # ══════════════════════════════════════════
    # NORTH CAROLINA — AOC-CVM-201 Complaint in Summary Ejectment
    # ══════════════════════════════════════════
    # RHODE ISLAND — District Court Eviction Answer
    # 4 pages, 51 fillable fields
    # ══════════════════════════════════════════
    "RI": {
        "name": "Rhode Island",
        "answer_form": "ri_eviction_answer.pdf",
        "fee_waiver_form": "ri_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "case_number": "Civil Action File NumberRow1",
            "date": "Date",
            "full_name": "PlaintiffPetitioner",
            "household_adults": "The PlaintiffPetitioner states that there are",
            "other_income_description": "income is",
            "phone": "Telephone Number",
        },
        "has_fillable_fields": True,
        "court_type": "District Court",
        "field_mapping": {
            "full_name": "DefendantTenant",
            "landlord_name": "PlaintiffLandlord",
            "case_number": "Civil Action File Number",
            "phone": "Telephone Number",
            "date": "Date",
            "defendant_address": "Address of the DefendantTenants Attorney or the DefendantTenant",
            "plaintiff_address": "Address of the PlaintiffLandlords Attorney or the PlaintiffLandlord",
            "bar_number": "Rhode Island Bar Number",
        },
        "defense_options": [
            {"key": "def_offered_refused", "label": "Offered rent but landlord refused", "field": "I have offered rent but the PlaintiffLandlord refused it I am still able and willing to pay"},
            {"key": "def_failed_maintain", "label": "Defense — landlord failed to maintain premises", "field": "I have a defense for nonpayment because the PlaintiffLandlord has failed to maintain the"},
            {"key": "def_justifiable", "label": "Legally justifiable defense for nonpayment", "field": "My rent has not been paid but I have a legally justifiable defense for not paying"},
            {"key": "def_lease_not_expired", "label": "Written lease not yet expired", "field": "I have a written lease which does not expire until"},
            {"key": "def_no_notice", "label": "Did not receive required notice", "field": "I have not received the required notice from the PlaintiffLandlord before this Complaint"},
            {"key": "def_retaliation", "label": "Retaliation for exercising legal rights", "field": "The PlaintiffLandlord is trying to evict me because I have exercised my legal rights by"},
        ],
        "notes": "RI District Court eviction answer. 51 fields across 4 pages. Has explicit defendant/plaintiff fields on page 1, defense checkboxes on page 2, certification on pages 3-4.",
    },

    # ══════════════════════════════════════════
    # COLORADO — JDF 103 Eviction Answer
    # 6 pages, 57 fillable fields (named form fields on page 1)
    # ══════════════════════════════════════════
    "CO": {
        "name": "Colorado",
        "answer_form": "co_eviction_answer.pdf",
        "fee_waiver_form": "co_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "case_number": "Case Number",
            "cash_on_hand": "10A.1",
            "checking_balance": "10A.2A",
            "child_care_expense": "9A.4",
            "county": "County",
            "date": "Sig1_Date",
            "email": "Email",
            "employment_income": "8A.0",
            "food_expense": "9A.3",
            "full_name": "Name",
            "medical_expense": "9A.5",
            "phone": "Phone",
            "printed_name": "Name",
            "real_estate_loan_owed": "10B.4B",
            "real_estate_value": "10B.4A",
            "receives_medicaid": "6.3",
            "receives_public_benefits": "6.1",
            "receives_snap": "6.2",
            "receives_ssi": "6.4",
            "receives_tanf": "6.5",
            "rent_or_mortgage": "9A.1",
            "savings_balance": "10A.2B",
            "self_employment_income": "8B.1",
            "total_monthly_expenses": "9A.8",
            "transportation_expense": "9A.6A",
            "unemployment_income": "8C.1",
            "utilities_expense": "9A.2",
            "vehicle_loan_owed": "10B.1C",
            "vehicle_make_model": "10B.1A",
            "vehicle_value": "10B.1B",
        },
        "has_fillable_fields": True,
        "court_type": "County Court",
        "field_mapping": {
            "full_name": "∆",
            "landlord_name": "π",
            "address": "Street address",
            "city": "City",
            "state": "State",
            "zip": "Zip",
            "phone": "Phone",
            "email": "Email",
            "case_number": "Case Number",
            "division": "Division",
            "courtroom": "Courtroom",
            "county": "Court County",
            "court_address": "Court Address",
        },
        "defense_options": [
            # Section 7A — Non-Payment Defenses
            {"key": "def_paid", "label": "I paid all rent owed", "field": "7A.1"},
            {"key": "def_attempted_pay", "label": "I tried to pay but landlord refused", "field": "7A.2"},
            {"key": "def_amount", "label": "I disagree with the amount claimed", "field": "7A.3"},
            {"key": "def_other", "label": "Other reasons rent not paid", "field": "7A.4"},
            # Section 7B — Habitability / Condition Defenses
            {"key": "def_repairs", "label": "Premises uninhabitable — landlord failed to maintain", "field": "7B.1"},
            {"key": "def_did_repairs", "label": "I paid for repairs landlord should have made", "field": "7B.2"},
            {"key": "def_landlord_breach", "label": "Landlord breached the rental agreement", "field": "7B.3"},
            # Section 7C — Notice Defenses
            {"key": "def_bad_notice", "label": "Improper or no notice", "field": "7C.1"},
            {"key": "def_wrong_reason", "label": "Wrong termination reason in notice", "field": "7C.2"},
            # Section 7D — Retaliation / Discrimination
            {"key": "def_retaliation", "label": "Retaliatory eviction", "field": "7D.1"},
            {"key": "def_discrimination", "label": "Discriminatory eviction", "field": "7D.2"},
            # Section 7E — Other Defenses
            {"key": "def_corrected", "label": "I corrected the lease violation", "field": "7E.1"},
            {"key": "def_accepted_rent", "label": "Landlord accepted rent after notice", "field": "7E.2"},
        ],
        "notes": "CO JDF 103 — 6 pages, 57 fillable fields. Page 1 has 14 named fields (∆=defendant, π=plaintiff). Pages 2-4 have structured defense sections 7A-7E with checkboxes for non-payment, habitability, notice, retaliation/discrimination, and other defenses.",
    },

    # ══════════════════════════════════════════
    # LOUISIANA — Eviction Answer (LSBA form)
    # 14 pages, 62 fillable fields (checkbox/defense based)
    # Data fields use overlay since the form has no Name/Case# text fields
    # ══════════════════════════════════════════
    "LA": {
        "name": "Louisiana",
        "answer_form": "la_eviction_answer.pdf",
        "fee_waiver_form": "la_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "Box Number or Street Address",
            "case_number": "Docket Number",
            "cash_on_hand": "Amount in Bank Account",
            "child_care_expense": "Daycare",
            "child_support_income": "Child Support",
            "county": "Parish",
            "debt_payments": "Total Monthly Credit Card Payment",
            "disability_income": "Disability",
            "employment_income": "Amount Paid/Month",
            "food_expense": "Food",
            "full_name": "Your Full Name",
            "household_children": "Under 18",
            "medical_expense": "Medical Expenses",
            "other_income_description": "Other Monthly Income Received",
            "phone": "Home Phone Number",
            "real_estate_loan_owed": "Balance Owed - House",
            "real_estate_value": "Value of Interest - House",
            "receives_snap": "Food Stamps",
            "receives_ssi": "SSI Support",
            "receives_tanf": "TANF",
            "rent_or_mortgage": "Monthly Rent",
            "total_monthly_expenses": "Total Monthly Expenses",
            "transportation_expense": "Transportation",
            "unemployment_income": "Unemployment Benefits",
            "utilities_expense": "Electricity",
            "vehicle_loan_owed": "Balance Owed - Auto",
            "vehicle_value": "Value of Interest - Auto",
        },
        "has_fillable_fields": True,
        "court_type": "District Court / City Court",
        "field_mapping": {},
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 200, "w": 300, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 72, "y": 230, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 400, "y": 90, "w": 200, "h": 20, "size": 11},
            "address": {"page": 1, "x": 72, "y": 260, "w": 300, "h": 20, "size": 11},
            "county": {"page": 1, "x": 72, "y": 170, "w": 200, "h": 20, "size": 11},
            "phone": {"page": 1, "x": 72, "y": 290, "w": 200, "h": 20, "size": 11},
        
            "court_name": {"page": 5, "x": 354, "y": 166, "w": 200, "h": 16, "size": 10},
            "date": {"page": 5, "x": 188, "y": 270, "w": 120, "h": 16, "size": 10},
            "defense_attempted_pay": {"page": 2, "x": 155, "y": 339, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 2, "x": 155, "y": 417, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 2, "x": 162, "y": 655, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 4, "x": 72, "y": 337, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 2, "x": 155, "y": 417, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 3, "x": 155, "y": 435, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 5, "x": 90, "y": 190, "w": 14, "h": 14, "size": 10},
            "email": {"page": 1, "x": 210, "y": 329, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 1, "x": 210, "y": 316, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 5, "x": 208, "y": 523, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 5, "x": 208, "y": 393, "w": 200, "h": 20, "size": 10},
            "court_name": {"page": 1, "x": 172, "y": 499, "w": 200, "h": 16, "size": 10},
            "date": {"page": 1, "x": 152, "y": 237, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 8, "x": 71, "y": 341, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 7, "x": 71, "y": 402, "w": 14, "h": 14, "size": 10},
            "defense_bad_notice": {"page": 5, "x": 54, "y": 91, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 8, "x": 54, "y": 210, "w": 14, "h": 14, "size": 10},
            "defense_not_owner": {"page": 4, "x": 70, "y": 594, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 6, "x": 107, "y": 185, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 90, "y": 405, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 7, "x": 71, "y": 558, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 8, "x": 54, "y": 231, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 5, "x": 54, "y": 502, "w": 14, "h": 14, "size": 10},
            "email": {"page": 6, "x": 192, "y": 384, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 11, "x": 172, "y": 119, "w": 200, "h": 20, "size": 10},
            "court_name": {"page": 1, "x": 394, "y": 74, "w": 200, "h": 16, "size": 10},
            "date": {"page": 1, "x": 152, "y": 616, "w": 120, "h": 16, "size": 10},
            "defense_attempted_pay": {"page": 2, "x": 72, "y": 236, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 2, "x": 72, "y": 512, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 2, "x": 72, "y": 278, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 2, "x": 72, "y": 278, "w": 14, "h": 14, "size": 10},
            "phone": {"page": 3, "x": 192, "y": 272, "w": 200, "h": 16, "size": 10}},
        "defense_options": [
            {"key": "def_continuance", "label": "Request continuance to reschedule hearing", "field": "I would like to request that the court grant a continuance and reschedule my hearing"},
            {"key": "def_negotiate", "label": "Negotiate move-out plan or payment date", "field": "I would like to negotiate a moveout plan or payment date with my landlord to avoid"},
            {"key": "def_exceptions", "label": "I have exceptions/defenses to the claims", "field": "I have exceptions andor defenses to the claims made in the eviction paperwork"},
            {"key": "def_moved_out", "label": "Already moved out — case is moot", "field": "I have moved out of the rental property so this eviction case is moot"},
            {"key": "def_no_written_notice", "label": "No written Notice to Vacate", "field": "The landlord did not issue a written Notice to Vacate that explains the reason for the"},
            {"key": "def_timeline_errors", "label": "Timeline errors with notice/service", "field": "There were timeline errors with the Notice to Vacate andor Rule for Possession"},
            {"key": "def_accepted_rent", "label": "Landlord accepted rent after notice", "field": "The landlord accepted some payment of rent after issuing me a Notice to Vacate"},
            {"key": "def_different_reasons", "label": "Notice and Rule state different reasons", "field": "The Notice to Vacate and the Rule for Possession state different reasons for"},
            {"key": "def_too_vague", "label": "Notice/Rule too vague to understand", "field": "The Notice to Vacate andor Rule for Possession is too vague for me to know how to"},
            {"key": "def_not_owner", "label": "Filer is not actual owner or agent", "field": "The person who filed the Rule for Possession is not the owner or the owners agent"},
            {"key": "def_early_court", "label": "Court date too soon after service", "field": "My court date is sooner than the third day after service of the court papers"},
            {"key": "def_early_notice", "label": "Notice to Vacate served too early", "field": "I was served a Notice to Vacate too early A longer notice period is required to"},
            {"key": "def_early_rule", "label": "Rule for Possession filed too early", "field": "The Rule for Possession was filed too early It was filed on"},
            {"key": "def_cure_required", "label": "Lease requires notice to cure violation", "field": "My lease requires that the landlord give me a notice to cure the violation or cease"},
            {"key": "def_ownership_interest", "label": "I have ownership interest in property", "field": "I have an ownership interest in the property I am being evicted from"},
            {"key": "def_lease_not_expired", "label": "Lease not expired, no reason given", "field": "My lease is not expired but my landlord did not provide a reason for eviction"},
            {"key": "def_subsidy_requires_reason", "label": "Housing subsidy requires reason for termination", "field": "My housing subsidy program requires that my landlord have a reason for not"},
            {"key": "def_other_exceptions", "label": "Other exceptions", "field": "Other exceptions"},
            {"key": "def_section8_protection", "label": "Section 8 / public housing protections", "field": "I live in public housing or projectbased Section 8 housing and the federally required"},
            {"key": "def_no_notice_section8", "label": "No notice — Section 8 voucher tenant", "field": "I did not receive a Notice to Vacate I have a tenantbased Section 8 voucher so"},
            {"key": "def_public_housing_no_good_cause", "label": "Public housing — no good cause shown", "field": "I live in public housing or a projectbased Section 8 unit and my landlord did not"},
            {"key": "def_need_time", "label": "Need time to prepare/gather evidence", "field": "I need time to prepare and gather evidence that I cannot reasonably obtain"},
            {"key": "def_health_issue", "label": "Health/medical issues affecting presentation", "field": "There are healthmedical issues which impact my ability to present my case"},
            {"key": "def_emergency", "label": "Emergency occurred", "field": "An emergency has occurred"},
            {"key": "def_disaster", "label": "Experienced a disaster", "field": "Ive experienced a disaster"},
            {"key": "def_seeking_lawyer", "label": "Trying to find a lawyer", "field": "Im trying to find a lawyer"},
            {"key": "def_other_continuance", "label": "Other reason for continuance", "field": "Other reason explain"},
            {"key": "def_want_moveout_plan", "label": "Want to negotiate move-out date", "field": "I would like to negotiate a moveout date with my landlord"},
            {"key": "def_want_payment_plan", "label": "Want to negotiate payment plan", "field": "I would like to negotiate a payment plan with my landlord"},
            {"key": "def_refused_rent", "label": "Landlord refused rent payments", "field": "My landlord refused my rent payments I have proof of my attempts to pay"},
            {"key": "def_accepted_late", "label": "Landlord accepted late payments before", "field": "My landlord has accepted late payments in the past I have proof of my late"},
            {"key": "def_not_violate_lease", "label": "I did not commit the lease violations", "field": "I did not commit the lease violations stated by my landlord"},
            {"key": "def_disability", "label": "Violation related to disability", "field": "The alleged violation of my lease is related to my physical or mental disability and I"},
            {"key": "def_repairs", "label": "Used rent money for repairs landlord ignored", "field": "I used my rent money to make repairs that my landlord did not take care of"},
            {"key": "def_domestic_violence", "label": "Eviction related to domestic violence", "field": "My eviction is related to domestic violence"},
            {"key": "def_other_defenses", "label": "Other defenses", "field": "I have some other defenses"},
            {"key": "def_no_notice", "label": "Did not receive Notice to Vacate", "field": "I did not receive a Notice to Vacate I have a tenantbased Section 8 voucher so"},
            {"key": "def_section8", "label": "Section 8 — don't owe rent claimed", "field": "I do not owe the rent because I am on Section 8 or another government housing"},
            {"key": "def_ownership", "label": "Ownership interest in property", "field": "I have an ownership interest in the property I am being evicted from"},
        ],
        "notes": "LA LSBA eviction answer form — 14 pages of checkbox defense fields only. No fillable name/case# fields on form, so data fields use overlay positions on page 1. 39 defense options mapped.",
    },

    # ══════════════════════════════════════════
    # TENNESSEE — Sworn Denial (General Sessions)
    # 2 pages, 20 fillable fields
    # ══════════════════════════════════════════
    "TN": {
        "name": "Tennessee",
        "answer_form": "tn_eviction_answer.pdf",
        "fee_waiver_form": "tn_fee_waiver.pdf",
        "overlay_positions": {
            "financial_summary": {"page": 1, "x": 50, "y": 50, "w": 500, "h": 200, "size": 9},
        
            "date": {"page": 1, "x": 179, "y": 238, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 1, "x": 87, "y": 222, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 1, "x": 70, "y": 435, "w": 14, "h": 14, "size": 10},
            "phone": {"page": 1, "x": 163, "y": 316, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 143, "y": 550, "w": 200, "h": 20, "size": 10}},

        "has_fillable_fields": True,
        "court_type": "General Sessions Court",
        "field_mapping": {
            "case_number": "file_number",
            "county": "county",
            "court_name": "court",
            "court_division": "division",
            "date": "date_1",
            "day": "day_2",
            "full_name": "name_1",
            "landlord_name": "plaintiff_1",
            "defendant_name": "defendant_1",
            "month": "mm_1",
            "year": "year_2",
            "hearing_at_1": "at the hearing 1",
            "hearing_at_2": "at the hearing 2",
            "hearing_at_3": "at the hearing 3",
            "hearing_at_4": "at the hearing 4",
            "certification_1": "cert_1",
            "defense_narrative": "at the hearing 1",
        },
        "notes": "TN Sworn Denial form — 20 text fields, NO defense checkboxes. Defense narrative text is auto-generated from intake answers and pre-filled into 'at the hearing 1' text area. Tenant can edit before filing.",
    
        "fee_waiver_overlay": {
            "address": {"page": 1, "x": 120, "y": 210, "w": 350, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 200, "y": 120, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 200, "y": 100, "w": 200, "h": 20, "size": 11},
            "date": {"page": 2, "x": 400, "y": 600, "w": 150, "h": 20, "size": 11},
            "full_name": {"page": 1, "x": 120, "y": 180, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 1, "x": 120, "y": 240, "w": 200, "h": 20, "size": 11}
        }},

    # ══════════════════════════════════════════
    # CALIFORNIA — UD-105 Answer Unlawful Detainer
    # 4 pages, 154 fillable fields
    # Fills attorney/party info section with defendant's data (pro se)
    # ══════════════════════════════════════════
    "CA": {
        "name": "California",
        "answer_form": "ca_ud105.pdf",
        "fee_waiver_form": "ca_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Superior Court",
        "field_mapping": {
            "case_number": "UD-105[0].Page1[0].P1Caption[0].CaptionSub[0].CaseNumber[0].CaseNumber[0]",
            "full_name": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Name[0]",
            "address": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Street[0]",
            "city": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].City[0]",
            "state": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].State[0]",
            "zip": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Zip[0]",
            "phone": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]",
            "email": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]",
            "county": "UD-105[0].Page1[0].P1Caption[0].CourtInfo[0].CrtCounty[0]",
            "printed_name": "UD-105[0].Page4[0].Sign[0].PrintName1[0]",
        },
        "fee_waiver_mapping": {
            # Page 1 — Personal Info
            "case_number": "FW-001[0].Page1[0].RightCaption[0].CaseNumber[0]",
            "full_name": "FW-001[0].Page1[0].List1[0].item1[0].PetitionerName1[0]",
            "address": "FW-001[0].Page1[0].List1[0].item1[0].PetitionerStrAddress[0]",
            "city": "FW-001[0].Page1[0].List1[0].item1[0].PetitionerCity[0]",
            "state_short": "FW-001[0].Page1[0].List1[0].item1[0].PetitionerState[0]",
            "zip": "FW-001[0].Page1[0].List1[0].item1[0].PetitionerZip[0]",
            "phone": "FW-001[0].Page1[0].List1[0].item1[0].PetitionerTel[0]",
            # Public Benefits (checkboxes)
            "receives_public_benefits": "FW-001[0].Page1[0].List5[0].Lia[0].PublicBenefitReceived[0]",
            "receives_snap": "FW-001[0].Page1[0].List5[0].Lia[0].PublicBenefitSNAP[0]",
            "receives_ssi": "FW-001[0].Page1[0].List5[0].Lia[0].PublicBenefitSSI[0]",
            "receives_medicaid": "FW-001[0].Page1[0].List5[0].Lia[0].PublicBenefitMediCal[0]",
            "receives_tanf": "FW-001[0].Page1[0].List5[0].Lia[0].PublicBenefitCalWORKSTANF[0]",
            "receives_county_assistance": "FW-001[0].Page1[0].List5[0].Lia[0].PublicBenefitCtyGA[0]",
            # Income threshold (checkbox — income below 200% FPL)
            "income_below_threshold": "FW-001[0].Page1[0].List5[0].Lib[0].GrossMonthIncomeLess[0]",
            # Page 2 — Financial Data
            "cash_on_hand": "FW-001[0].Page2[0].List10[0].Lia[0].Cash[0]",
            "monthly_gross_income": "FW-001[0].Page2[0].List8[0].Lib[0].TotalIncome[0]",
            "rent_or_mortgage": "FW-001[0].Page2[0].List11[0].Lib[0].ExpenseHousing[0]",
            "food_expense": "FW-001[0].Page2[0].List11[0].Lic[0].ExpenseFoodSupplies[0]",
            "utilities_expense": "FW-001[0].Page2[0].List11[0].Lid[0].ExpenseUtilitiesPhone[0]",
            "transportation_expense": "FW-001[0].Page2[0].List11[0].Lik[0].ExpenseTransportation[0]",
            "medical_expense": "FW-001[0].Page2[0].List11[0].Lig[0].ExpenseMedicalDental[0]",
            "child_care_expense": "FW-001[0].Page2[0].List11[0].Lii[0].ExpenseSchoolChildCare[0]",
            "total_monthly_expenses": "FW-001[0].Page2[0].List11[0].Total[0].Totalmonthlyexpenses[0]",
            "debt_payments": "FW-001[0].Page2[0].List11[0].Lil[0].InstallmentPaymentAmount1[0]",
            # Vehicle info
            "vehicle_make_model": "FW-001[0].Page2[0].List10[0].Lic[0].VehicleMakeYr1[0]",
            "vehicle_value": "FW-001[0].Page2[0].List10[0].Lic[0].VehicleFairMarketVal1[0]",
            "vehicle_loan_owed": "FW-001[0].Page2[0].List10[0].Lic[0].VehicleAmountOwed1[0]",
            # Signature
            "date": "FW-001[0].Page1[0].Sign[0].SigDate[0]",
            "printed_name": "FW-001[0].Page1[0].Sign[0].PetitionerName[0]",
        },
        "static_values": {
            "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].AttyFirm[0]": "In Pro Per",
        },
        "defense_options": [
            # Section 3 — Affirmative Defenses (CA UD-105)
            {"key": "def_bad_notice", "label": "Notice to quit is not proper (3a)", "field": "UD-105[0].Page1[0].List3[0].Lia[0].Check8[0]"},
            {"key": "def_bad_notice", "label": "Service of notice was not proper (3b)", "field": "UD-105[0].Page1[0].List3[0].Lib[0].Check9[0]"},
            {"key": "def_waived", "label": "Plaintiff waived/changed/canceled notice (3c)", "field": "UD-105[0].Page1[0].List3[0].Lic[0].Check10[0]"},
            {"key": "def_attempted_pay", "label": "Tendered payment of rent demanded (3d)", "field": "UD-105[0].Page1[0].List3[0].li3d[0].Check8[0]"},
            {"key": "def_retaliation", "label": "Eviction is retaliatory (3e)", "field": "UD-105[0].Page1[0].List3[0].Lie[0].Check11[0]"},
            {"key": "def_discrimination", "label": "Eviction is discriminatory (3f)", "field": "UD-105[0].Page1[0].List3[0].Lif[0].Check12[0]"},
            {"key": "def_repairs", "label": "Breach of warranty of habitability (3g)", "field": "UD-105[0].Page2[0].List3[0].Lig[0].Check13[0]"},
            {"key": "def_did_repairs", "label": "Repair and deduct (3k)", "field": "UD-105[0].Page2[0].List3[0].Lij[0].Check21[0]"},
            {"key": "def_accepted_rent", "label": "Landlord accepted rent (3k2)", "field": "UD-105[0].Page2[0].List3[0].Lik[0].Check22[0]"},
            {"key": "def_other", "label": "Other affirmative defenses (3l)", "field": "UD-105[0].Page2[0].List3[0].l3il[0].Check23[0]"},
        ],
        "notes": "CA UD-105 — 154 fields, complex XFA dotted paths. Maps defendant (pro se) into AttyPartyInfo section. 10 defense checkboxes mapped from Sections 3a-3l for improper notice, improper service, waiver, tender, retaliation, discrimination, habitability, repair-and-deduct, accepted rent, and other.",
    },

    # ══════════════════════════════════════════
    # ARKANSAS — Unlawful Detainer Answer Packet
    # 11 pages (scanned, overlay needed)
    # ══════════════════════════════════════════
    "AR": {
        "name": "Arkansas",
        "answer_form": "ar_eviction_answer.pdf",
        "fee_waiver_form": "ar_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "case_number": "NO",
            "county": "COUNTY OF",
            "date": "day of",
            "full_name": "IN RE PETITION OF",
            "cash_on_hand": "has the sum of",
        },
        "has_fillable_fields": False,
        "court_type": "District Court",
        "overlay_positions": {
            "county": {"page": 6, "x": 300, "y": 148, "w": 200, "h": 20, "size": 11},
            "court_name": {"page": 6, "x": 300, "y": 170, "w": 250, "h": 20, "size": 11},
            "plaintiff_name": {"page": 6, "x": 300, "y": 192, "w": 250, "h": 20, "size": 11},
            "case_number": {"page": 6, "x": 300, "y": 218, "w": 200, "h": 20, "size": 11},
            "defendant_name": {"page": 6, "x": 300, "y": 244, "w": 250, "h": 20, "size": 11},
        
            "date": {"page": 3, "x": 213, "y": 443, "w": 120, "h": 16, "size": 10},
            "defense_bad_notice": {"page": 9, "x": 54, "y": 354, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 2, "x": 48, "y": 213, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 2, "x": 48, "y": 368, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 2, "x": 48, "y": 64, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 2, "x": 48, "y": 277, "w": 14, "h": 14, "size": 10},
            "phone": {"page": 2, "x": 186, "y": 402, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 3, "x": 215, "y": 364, "w": 200, "h": 20, "size": 10},
            "court_name": {"page": 1, "x": 138, "y": 144, "w": 200, "h": 16, "size": 10},
            "date": {"page": 1, "x": 171, "y": 640, "w": 120, "h": 16, "size": 10},
            "defense_accepted_rent": {"page": 2, "x": 73, "y": 266, "w": 14, "h": 14, "size": 10},
            "defense_amount": {"page": 2, "x": 89, "y": 486, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 324, "y": 639, "w": 14, "h": 14, "size": 10},
            "defense_bad_notice": {"page": 2, "x": 71, "y": 661, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 3, "x": 73, "y": 550, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 2, "x": 72, "y": 81, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 3, "x": 72, "y": 131, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 73, "y": 598, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 1, "x": 73, "y": 611, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 1, "x": 73, "y": 692, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 1, "x": 73, "y": 678, "w": 14, "h": 14, "size": 10},
            "email": {"page": 1, "x": 157, "y": 118, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 1, "x": 157, "y": 107, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 4, "x": 220, "y": 275, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 136, "y": 265, "w": 200, "h": 20, "size": 10},
            "defense_narrative": {"page": 8, "x": 90, "y": 355, "w": 430, "h": 190, "size": 9}},
        "notes": "AR unlawful detainer answer packet — 11 pages. Page 8 has narrative defense text area where tenant writes reasons. We pre-fill this with formatted defense explanations based on intake answers. Remaining pages are instructions (1-5) and signature pages (9-11).",
    },

    # ══════════════════════════════════════════
    # ARIZONA — Answer (LJEA00004F) + MHJCEA2I Instructions
    # Answer form is 2 pages, scanned (overlay only)
    # ══════════════════════════════════════════
    "AZ": {
        "name": "Arizona",
        "answer_form": "az_answer_form.pdf",
        "instructions_form": "az_eviction_answer.pdf",
        "fee_waiver_form": "az_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "Address if not protected",
            "bank_balances": "BankBalances",
            "case_number": "Case Number",
            "county": "COUNTY",
            "date": "Date",
            "email": "Email Address",
            "full_name": "Person Filing",
            "monthly_gross_income": "GrossMonthlyIncome",
            "monthly_net_income": "TakehomePay",
            "phone": "Telephone",
            "printed_name": "ApplicantName",
            "receives_snap": "FoodStamps",
            "receives_tanf": "TANF",
            "total_monthly_expenses": "MonthlyExpenses",
        },
        "has_fillable_fields": False,
        "court_type": "Justice Court / Superior Court",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 400, "w": 300, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 72, "y": 420, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 2, "x": 130, "y": 37, "w": 200, "h": 20, "size": 11},
            "address": {"page": 1, "x": 72, "y": 440, "w": 300, "h": 20, "size": 10},
            "phone": {"page": 1, "x": 72, "y": 460, "w": 200, "h": 20, "size": 10},
            "county": {"page": 1, "x": 72, "y": 380, "w": 200, "h": 20, "size": 10},
            "date": {"page": 1, "x": 400, "y": 460, "w": 150, "h": 20, "size": 10},
            # Defense checkbox overlay positions (OCR-verified at 300 DPI)
            "def_dismiss": {"page": 1, "x": 73, "y": 526, "w": 14, "h": 14, "size": 10},
            "def_contest": {"page": 1, "x": 109, "y": 544, "w": 14, "h": 14, "size": 10},
            "def_not_owner": {"page": 1, "x": 109, "y": 561, "w": 14, "h": 14, "size": 10},
            "def_not_owner2": {"page": 1, "x": 109, "y": 595, "w": 14, "h": 14, "size": 10},
            "def_bad_notice": {"page": 1, "x": 109, "y": 630, "w": 14, "h": 14, "size": 10},
            "def_other": {"page": 1, "x": 73, "y": 653, "w": 14, "h": 14, "size": 10},
            "def_repairs": {"page": 2, "x": 73, "y": 187, "w": 14, "h": 14, "size": 10},
        
            "court_name": {"page": 1, "x": 172, "y": 238, "w": 200, "h": 16, "size": 10},
            "defense_other": {"page": 1, "x": 90, "y": 648, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 2, "x": 126, "y": 105, "w": 14, "h": 14, "size": 10},
            "email": {"page": 1, "x": 192, "y": 172, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 2, "x": 430, "y": 522, "w": 200, "h": 20, "size": 10},
            "defense_narrative": {"page": 1, "x": 72, "y": 548, "w": 430, "h": 80, "size": 9}},
        "notes": "AZ answer form (LJEA00004F) — scanned PDF, no fillable fields. Overlay positions cover all essential tenant/landlord/case fields plus 7 defense checkboxes (OCR-verified). MHJCEA2I is the instructions companion PDF.",
    },

    # ══════════════════════════════════════════
    # FLORIDA — Form 1.947(b) Answer Residential Eviction (generated)
    # Standardized form generated by the packet system
    # ══════════════════════════════════════════
    "FL": {
        "name": "Florida",
        "answer_form": "answer_form_917.pdf",
        "fee_waiver_form": "fl_fee_waiver.pdf",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 400, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 420, "y": 126, "w": 150, "h": 20, "size": 11},
            "financial_summary": {"page": 1, "x": 50, "y": 500, "w": 500, "h": 200, "size": 9},
        
            "date": {"page": 1, "x": 160, "y": 411, "w": 120, "h": 16, "size": 10},
            "defense_accepted_rent": {"page": 2, "x": 80, "y": 104, "w": 14, "h": 14, "size": 10},
            "defense_amount": {"page": 1, "x": 80, "y": 355, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 80, "y": 557, "w": 14, "h": 14, "size": 10},
            "defense_bad_notice": {"page": 2, "x": 80, "y": 215, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 2, "x": 80, "y": 141, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 2, "x": 80, "y": 57, "w": 14, "h": 14, "size": 10},
            "defense_not_owner": {"page": 2, "x": 80, "y": 178, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 2, "x": 80, "y": 253, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 62, "y": 312, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 1, "x": 80, "y": 452, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 1, "x": 80, "y": 689, "w": 14, "h": 14, "size": 10},
            "defense_waived": {"page": 1, "x": 80, "y": 641, "w": 14, "h": 14, "size": 10},
            "email": {"page": 2, "x": 426, "y": 579, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 2, "x": 426, "y": 562, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 2, "x": 406, "y": 513, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 2, "x": 406, "y": 497, "w": 200, "h": 20, "size": 10}},
        "has_fillable_fields": True,
        "court_type": "County Court",
        "field_mapping": {
            "full_name": "Defendant(s)",
            "landlord_name": "Plaintiff(s)",
            "case_number": "Case number",
            "phone": "Telephone number",
            "email": "E-mail Address",
            "address": "Address",
            "date": "Date",
            "printed_name": "Print Name",
        },
        "defense_options": [
            {"key": "def_repairs", "label": "Landlord did not make repairs", "field": "The landlord did not make repairs"},
            {"key": "def_amount", "label": "I do not owe the amount claimed", "field": "I do not owe the total amount of rent"},
            {"key": "def_attempted_pay", "label": "I attempted/offered to pay", "field": "I attempted/offered to pay all the rent due"},
            {"key": "def_paid", "label": "I paid the rent demanded", "field": "I paid the rent demanded by the the lanlord in the notice to pay rent"},
            {"key": "def_waived", "label": "Landlord waived/changed/canceled notice", "field": "The landlord waived, changed, or canceled the notice"},
            {"key": "def_retaliation", "label": "Retaliatory eviction", "field": "The landlord filed the eviction notice"},
            {"key": "def_fair_housing", "label": "Fair Housing Act violation", "field": "The landlord filed the eviction in violation"},
            {"key": "def_accepted_rent", "label": "Landlord accepted rent after notice", "field": "The landlord accepted rent from me after sending me the notice to terminate"},
            {"key": "def_corrected", "label": "I already corrected the violations", "field": "I already corrected the violations claime by the landlord"},
            {"key": "def_not_owner", "label": "Landlord is not the owner", "field": "The landlord is not the owner of the property"},
            {"key": "def_bad_notice", "label": "No notice or legally incorrect notice", "field": "I did not receive the notice to terminate or the notice was legally incorrect"},
            {"key": "def_other", "label": "Other defenses", "field": "Other defenses l"},
        ],
        "notes": "FL Form 1.947(b) Answer — Residential Eviction. 54 fillable fields across 2 pages (Miami-Dade clerk version). Covers all 12 defenses with explanation fields, jury trial selection, and signature block.",
    
        "fee_waiver_overlay": {
            "case_number": {"page": 1, "x": 350, "y": 200, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 72, "y": 230, "w": 200, "h": 20, "size": 11},
            "date": {"page": 5, "x": 72, "y": 600, "w": 150, "h": 20, "size": 11},
            "full_name": {"page": 1, "x": 72, "y": 200, "w": 300, "h": 20, "size": 11}
        }},

    # ══════════════════════════════════════════
    # MINNESOTA — Housing Court Eviction Answer (HOU202)
    # 4 pages, scanned (overlay only)
    # ══════════════════════════════════════════
    "MN": {
        "name": "Minnesota",
        "answer_form": "mn_eviction_answer.pdf",
        "fee_waiver_form": "mn_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "District Court (Housing)",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 200, "y": 277, "w": 200, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 200, "y": 188, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 75, "y": 106, "w": 200, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 420, "y": 126, "w": 150, "h": 20, "size": 11},
            "address": {"page": 1, "x": 72, "y": 327, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 1, "x": 72, "y": 347, "w": 200, "h": 20, "size": 10},
            "date": {"page": 1, "x": 400, "y": 347, "w": 150, "h": 20, "size": 10},
            # Defense checkbox overlay (OCR-verified at 600 DPI)
            "def_amount": {"page": 2, "x": 93, "y": 470, "w": 14, "h": 14, "size": 10},
            "def_bad_notice": {"page": 2, "x": 93, "y": 519, "w": 14, "h": 14, "size": 10},
            "def_other": {"page": 2, "x": 93, "y": 705, "w": 14, "h": 14, "size": 10},
            "def_repairs": {"page": 3, "x": 95, "y": 162, "w": 14, "h": 14, "size": 10},
            "def_other2": {"page": 3, "x": 101, "y": 288, "w": 14, "h": 14, "size": 10},
        
            "financial_summary": {"page": 1, "x": 50, "y": 50, "w": 500, "h": 200, "size": 9},
        
            "court_name": {"page": 1, "x": 531, "y": 88, "w": 200, "h": 16, "size": 10},
            "defense_bad_notice": {"page": 3, "x": 75, "y": 632, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 3, "x": 89, "y": 175, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 3, "x": 94, "y": 158, "w": 14, "h": 14, "size": 10},
            "email": {"page": 4, "x": 412, "y": 376, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 4, "x": 396, "y": 246, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 4, "x": 396, "y": 246, "w": 200, "h": 20, "size": 10},
            "defense_repairs": {"page": 3, "x": 94, "y": 158, "w": 14, "h": 14, "size": 10},
            "defense_narrative": {"page": 3, "x": 72, "y": 250, "w": 450, "h": 200, "size": 9}},
        "notes": "MN HOU202 Housing Court Eviction Answer — scanned PDF. Data fields on page 1 via overlay. Defense checkboxes on pages 2-3 (Q5=amount dispute, Q6=improper notice, Q8=lease dispute, Q9=repairs, Q10=other). OCR-verified at 600 DPI.",
    
        "fee_waiver_overlay": {
            "case_number": {"page": 1, "x": 350, "y": 100, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 300, "y": 100, "w": 200, "h": 20, "size": 11},
            "date": {"page": 6, "x": 72, "y": 600, "w": 150, "h": 20, "size": 11},
            "full_name": {"page": 1, "x": 72, "y": 200, "w": 300, "h": 20, "size": 11}
        }},

    # ══════════════════════════════════════════
    # NEVADA — Summary Eviction Answer (Nonpayment)
    # 65 fillable fields across 4 pages
    # ══════════════════════════════════════════
    "NV": {
        "name": "Nevada",
        "answer_form": "nv_answer_nonpayment.pdf",
        "fee_waiver_form": "nv_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "Address",
            "case_number": "Case Number",
            "child_care_expense": "Child Care",
            "county": "County",
            "date": "Date",
            "email": "Email",
            "employment_income": "Wages",
            "food_expense": "Food",
            "full_name": "Name",
            "household_adults": "Total Adults",
            "household_children": "Total Children",
            "medical_expense": "Medical Expenses",
            "phone": "Phone",
            "printed_name": "Name",
            "receives_child_care_assistance": "Child Care Subsidy",
            "receives_energy_assistance": "Energy Asst",
            "receives_medicaid": "Medicaid",
            "receives_public_benefits": "Public Assistance",
            "receives_public_housing": "Public Housing",
            "receives_snap": "SNAP",
            "receives_ssi": "SSI",
            "receives_tanf": "TANF",
            "rent_or_mortgage": "Rent / Mortgage",
            "total_monthly_expenses": "Total Expenses",
            "transportation_expense": "Transportation",
            "utilities_expense": "Utilities",
        },
        "has_fillable_fields": True,
        "court_type": "Justice Court",
        "field_mapping": {
            "full_name": "Name",
            "landlord_name": "s Name",
            "case_number": "Case No",
            "address": "Address",
            "city_state_zip": "CityStateZip",
            "phone": "Phone",
            "email": "EMail",
            "date": "Date",
            "court_name": "CourtSelect",
            "department": "Dept No",
            "printed_name": "Print your name",
        },
        "defense_options": [
            {"key": "def_moved_out", "label": "I moved out and returned keys", "field": "I moved out and gave my keys to the landlord"},
            {"key": "def_disagree_amount", "label": "I disagree with the rent amount claimed", "field": "I disagree with the amount of rent the Landlord claims I owe"},
            {"key": "def_rent_paid", "label": "My rent is paid in full", "field": "My rent is paid in full"},
            {"key": "def_costs_not_rent", "label": "Amount includes costs/fees that are not rent", "field": "The rent amount in the notice includes costs or fees that are not regular rent or late fees"},
            {"key": "def_tried_to_pay", "label": "I tried to pay rent but landlord refused", "field": "I tried to pay my full rent on insert date"},
            {"key": "def_partial_payment", "label": "Landlord accepted partial payment", "field": "Landlord accepted partial payment of my rent on this date"},
            {"key": "def_late_fee", "label": "Late fee exceeds 5% of rent", "field": "Landlord is charging a late fee more than 5 of regular rent"},
            {"key": "def_no_free_pay", "label": "No free way to pay rent provided", "field": "Landlord has not provided a free way to pay the rent Landlord is required to provide a way for rent to be"},
            {"key": "def_repairs", "label": "Corrected habitability problem, deducting from rent", "field": "I corrected a habitability problem at my rental unit and am removing the cost from my rent"},
            {"key": "def_bad_notice", "label": "Notice was not properly served", "field": "Landlords notice was not served as required by law or the notice did not in other ways"},
            {"key": "def_discrimination", "label": "Discrimination (Fair Housing Act)", "field": "Landlord is discriminating against me in violation of the Federal Fair Housing Act or"},
            {"key": "def_retaliation", "label": "Retaliation for protected acts", "field": "Landlord is retaliating against me for taking part in certain protected acts"},
            {"key": "def_foreclosure", "label": "Property foreclosed on — new owner issues", "field": "I am a tenant in a property that has been foreclosed on and sold  The new owner"},
            {"key": "def_other", "label": "Other defenses (explain below)", "field": "Other explain below"},
        ],
        "notes": "NV Summary Eviction Answer — Nonpayment of Rent. 65 fields across 4 pages. Covers tenant info, defenses, interpreter request, and certificate of service.",
    },

    # ══════════════════════════════════════════
    # OREGON — Eviction Answer (FED Answer)
    # 2 pages, scanned (overlay only)
    # ══════════════════════════════════════════
    "OR": {
        "name": "Oregon",
        "answer_form": "or_eviction_answer.pdf",
        "fee_waiver_form": "or_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Circuit Court",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 100, "w": 250, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 72, "y": 120, "w": 250, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 300, "y": 72, "w": 200, "h": 20, "size": 11},
            "address": {"page": 1, "x": 72, "y": 140, "w": 300, "h": 20, "size": 10},
            "phone": {"page": 1, "x": 72, "y": 160, "w": 200, "h": 20, "size": 10},
            "county": {"page": 1, "x": 72, "y": 80, "w": 200, "h": 20, "size": 10},
            "date": {"page": 1, "x": 400, "y": 160, "w": 150, "h": 20, "size": 10},
            # Defense checkbox overlay (OCR-verified at 600 DPI)
            "def_repairs": {"page": 1, "x": 91, "y": 293, "w": 14, "h": 14, "size": 10},
            "def_corrected": {"page": 1, "x": 91, "y": 336, "w": 14, "h": 14, "size": 10},
            "def_retaliation": {"page": 1, "x": 91, "y": 348, "w": 14, "h": 14, "size": 10},
            "def_victim_status": {"page": 1, "x": 91, "y": 373, "w": 14, "h": 14, "size": 10},
            "def_paid": {"page": 1, "x": 91, "y": 399, "w": 14, "h": 14, "size": 10},
            "def_attempted_pay": {"page": 1, "x": 91, "y": 411, "w": 14, "h": 14, "size": 10},
            "def_rental_assistance": {"page": 1, "x": 109, "y": 436, "w": 14, "h": 14, "size": 10},
            "def_bad_notice": {"page": 1, "x": 91, "y": 448, "w": 14, "h": 14, "size": 10},
            "def_other": {"page": 1, "x": 91, "y": 461, "w": 14, "h": 14, "size": 10},
        
            "financial_summary": {"page": 1, "x": 50, "y": 50, "w": 500, "h": 200, "size": 9},
        
            "court_name": {"page": 1, "x": 172, "y": 57, "w": 200, "h": 16, "size": 10},
            "date": {"page": 1, "x": 178, "y": 359, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 1, "x": 111, "y": 597, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 111, "y": 645, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 2, "x": 111, "y": 328, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 2, "x": 111, "y": 448, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 370, "y": 248, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 2, "x": 99, "y": 160, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 2, "x": 111, "y": 496, "w": 14, "h": 14, "size": 10},
            "email": {"page": 1, "x": 192, "y": 233, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 1, "x": 192, "y": 214, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 3, "x": 477, "y": 687, "w": 200, "h": 20, "size": 10},
            "defense_corrected": {"page": 1, "x": 84, "y": 332, "w": 14, "h": 14, "size": 10},
            "defense_other": {"page": 1, "x": 84, "y": 457, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 84, "y": 395, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 1, "x": 84, "y": 289, "w": 14, "h": 14, "size": 10},
            "defense_retaliation": {"page": 1, "x": 89, "y": 357, "w": 14, "h": 14, "size": 10},
            "email": {"page": 1, "x": 192, "y": 702, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 1, "x": 172, "y": 627, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 172, "y": 627, "w": 200, "h": 20, "size": 10},
            "defense_accepted_rent": {"page": 1, "x": 84, "y": 420, "w": 14, "h": 14, "size": 10},
            "defense_attempted_pay": {"page": 1, "x": 84, "y": 408, "w": 14, "h": 14, "size": 10},
            "defense_bad_notice": {"page": 1, "x": 84, "y": 445, "w": 14, "h": 14, "size": 10},
            "defense_corrected": {"page": 1, "x": 84, "y": 333, "w": 14, "h": 14, "size": 10},
            "defense_discrimination": {"page": 1, "x": 84, "y": 370, "w": 14, "h": 14, "size": 10},
            "defense_not_owner": {"page": 1, "x": 84, "y": 482, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 84, "y": 395, "w": 14, "h": 14, "size": 10},
            "defense_narrative": {"page": 1, "x": 72, "y": 490, "w": 450, "h": 120, "size": 9}},
        "notes": "OR FED Answer — scanned PDF with 10 checkbox defenses (OCR-verified at 600 DPI). Overlay positions for essential fields on page 1 caption area.",
    
        "fee_waiver_overlay": {
            "case_number": {"page": 1, "x": 350, "y": 100, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 72, "y": 80, "w": 200, "h": 20, "size": 10},
            "full_name": {"page": 1, "x": 72, "y": 100, "w": 300, "h": 20, "size": 11}
        }},

    # ══════════════════════════════════════════
    # MICHIGAN — DC 111a Answer, Nonpayment of Rent
    # 48 fillable fields across 2 pages (replaced landlord notice form)
    # ══════════════════════════════════════════
    "MI": {
        "name": "Michigan",
        "answer_form": "mi_eviction_answer.pdf",
        "fee_waiver_form": "mi_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "assets_description": "Assets",
            "case_number": "caseno",
            "county": "county",
            "date": "Date",
            "full_name": "dname",
            "household_adults": "Number in household",
            "monthly_gross_income": "My Gross Household Income is in Dollars",
            "obligations_description": "Obligations",
            "other_income_description": "My Source Of Income Is",
            "receives_medicaid": "Medicaid",
            "receives_public_benefits": "Option 1 of 2: I Receive Public Assistance Because Of Indigence",
            "receives_snap": "Food Assistance Program",
            "receives_ssi": "Supplemental Security Income (SSI)",
            "receives_tanf": "Family Independence Program",
        },
        "has_fillable_fields": True,
        "court_type": "District Court",
        "field_mapping": {
            "county": "Judicial district",
            "case_number": "Case number",
            "court_name": "Court address",
            "full_name": "Defendant name, address, and telephone number",
            "landlord_name": "Plaintiff name, address, and telephone number",
            "date": "Date",
            "printed_name": "Enter defendant or attorney signature",
        },
        "defense_options": [
            {"key": "def_jury_trial", "label": "I demand a jury trial", "field": "1. I demand a jury trial"},
            {"key": "def_agree_3", "label": "Agree with paragraph 3", "field": "agree 3"},
            {"key": "def_disagree_3", "label": "Disagree with paragraph 3", "field": "disagree 3"},
            {"key": "def_agree_4", "label": "Agree with paragraph 4", "field": "agree 4"},
            {"key": "def_disagree_4", "label": "Disagree with paragraph 4", "field": "disagree 4"},
            {"key": "def_agree_5", "label": "Agree with paragraph 5", "field": "agree 5"},
            {"key": "def_disagree_5", "label": "Disagree with paragraph 5", "field": "disagree 5"},
            {"key": "def_agree_6", "label": "Agree with paragraph 6", "field": "agree 6"},
            {"key": "def_disagree_6", "label": "Disagree with paragraph 6", "field": "disagree 6"},
            {"key": "def_agree_7", "label": "Agree with paragraph 7", "field": "agree 7"},
            {"key": "def_disagree_7", "label": "Disagree with paragraph 7", "field": "disagree 7"},
            {"key": "def_agree_8", "label": "Agree with paragraph 8", "field": "8. I agree that"},
            {"key": "def_disagree_8", "label": "Disagree with paragraph 8", "field": "8. disagree that"},
            {"key": "def_agree_9", "label": "Agree with paragraph 9", "field": "9. I agree"},
            {"key": "def_disagree_9", "label": "Disagree with paragraph 9", "field": "9. disagree"},
            {"key": "def_agree_10", "label": "Agree with paragraph 10", "field": "10 I agree"},
            {"key": "def_disagree_10", "label": "Disagree with paragraph 10", "field": "10 disagree"},
        ],
        "notes": "MI DC 111a Answer — Nonpayment of Rent. 48 fields across 2 pages with agree/disagree paragraph structure. Defendant and plaintiff fields are composite (name+address+phone in one field).",
    },

    # ══════════════════════════════════════════
    # MASSACHUSETTS — Summary Process (Eviction) Answer
    # 3 pages, 47 fillable fields — Housing Court
    # ══════════════════════════════════════════
    "MA": {
        "name": "Massachusetts",
        "answer_form": "ma_eviction_answer.pdf",
        "fee_waiver_form": "ma_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "address": "Street and number",
            "case_number": "Case Name and Number if known",
            "full_name": "Name of applicant",
            "household_adults": "persons consisting of myself and",
            "other_income_description": "List any other available household income for the checked period on this line",
            "receives_medicaid": "Medicaid MassHealth",
            "receives_public_benefits": "A I receive public assistance under check form of public assistance received",
            "receives_ssi": "Supplemental Security Income SSI",
            "receives_tanf": "Transitional Aid to Families with Dependent Children TAFDC",
        },
        "has_fillable_fields": True,
        "court_type": "Housing Court",
        "field_mapping": {
            "case_number": "Docket#",
            "county": "County",
            "court_name": "HOUSING COURT DIVISION",
            "landlord_name": "Plaintiff_Name",
            "full_name": "Defendant_Name",
            "submitted_name": "SubmittedBy_Name",
            "court_date": "Trial_Date",
            "address": "SubmittedBy_1Address",
            "submitted_address2": "SubmittedBy_2Address",
        },
        "defense_options": [
            {"key": "def_conditions", "label": "Poor conditions / landlord failed to repair", "field": "Check Box74"},
            {"key": "def_retaliation", "label": "Retaliatory eviction", "field": "Check Box75"},
            {"key": "def_discrimination", "label": "Discrimination", "field": "Check Box76"},
            {"key": "def_no_notice", "label": "Improper notice / no notice to quit", "field": "Check Box77"},
            {"key": "def_rent_paid", "label": "Rent has been paid", "field": "Check Box78"},
            {"key": "def_amount_wrong", "label": "Amount claimed is incorrect", "field": "Check Box79"},
            {"key": "def_waiver", "label": "Landlord waived right to evict", "field": "Check Box80"},
            {"key": "def_lease_violation", "label": "No lease violation", "field": "Check Box82"},
            {"key": "def_cured", "label": "Lease violation already cured", "field": "Check Box83"},
            {"key": "def_no_breach", "label": "No breach of lease", "field": "Check Box84"},
            {"key": "def_other", "label": "Other defenses", "field": "Check Box86"},
        ],
        "notes": "MA Summary Process Answer — Housing Court. 47 fillable fields across 3 pages. Page 1: case caption. Page 2: defense checkboxes + explanations. Page 3: counterclaims and certificate of service.",
    },

    # ══════════════════════════════════════════
    # NEW MEXICO — 4-907 Answer to Petition for Restitution
    # 1 page, scanned (overlay only)
    # ══════════════════════════════════════════
    "NM": {
        "name": "New Mexico",
        "answer_form": "nm_eviction_answer.pdf",
        "fee_waiver_form": "nm_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Metropolitan Court",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 100, "y": 120, "w": 300, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 100, "y": 140, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 250, "y": 80, "w": 200, "h": 20, "size": 11},
            "address": {"page": 1, "x": 100, "y": 160, "w": 300, "h": 20, "size": 10},
            "phone": {"page": 1, "x": 100, "y": 180, "w": 200, "h": 20, "size": 10},
            "county": {"page": 1, "x": 100, "y": 100, "w": 150, "h": 20, "size": 10},
            "date": {"page": 1, "x": 350, "y": 180, "w": 150, "h": 20, "size": 10},
            # Defense narrative text area — fills the "because:" blank lines
            "defense_narrative": {"page": 1, "x": 36, "y": 210, "w": 540, "h": 350, "size": 9},
        
            "financial_summary": {"page": 1, "x": 50, "y": 50, "w": 500, "h": 200, "size": 9},
        
            "court_name": {"page": 1, "x": 423, "y": 223, "w": 200, "h": 16, "size": 10},
            "defense_other": {"page": 2, "x": 54, "y": 614, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 3, "x": 90, "y": 165, "w": 14, "h": 14, "size": 10},
            "phone": {"page": 2, "x": 192, "y": 350, "w": 200, "h": 16, "size": 10},
            "printed_name": {"page": 3, "x": 424, "y": 392, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 3, "x": 424, "y": 392, "w": 200, "h": 20, "size": 10},
            "date": {"page": 2, "x": 131, "y": 347, "w": 120, "h": 16, "size": 10},
            "defense_amount": {"page": 1, "x": 156, "y": 360, "w": 14, "h": 14, "size": 10},
            "defense_paid": {"page": 1, "x": 229, "y": 90, "w": 14, "h": 14, "size": 10},
            "defense_repairs": {"page": 1, "x": 60, "y": 636, "w": 14, "h": 14, "size": 10},
            "phone": {"page": 1, "x": 620, "y": 125, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 2, "x": 406, "y": 347, "w": 200, "h": 20, "size": 10},
            "defense_amount": {"page": 1, "x": 54, "y": 304, "w": 14, "h": 14, "size": 10},
            "printed_name": {"page": 1, "x": 136, "y": 729, "w": 200, "h": 16, "size": 10},
            "signature": {"page": 1, "x": 460, "y": 473, "w": 200, "h": 20, "size": 10}},
        "notes": "NM 4-907 Answer to Petition for Restitution — single-page form. Overlay fills data fields and pre-fills defense narrative in the 'because:' blank area (lines 1-5).",
    
        "fee_waiver_overlay": {
            "county": {"page": 1, "x": 300, "y": 120, "w": 200, "h": 20, "size": 11},
            "date": {"page": 5, "x": 72, "y": 600, "w": 150, "h": 20, "size": 11},
            "full_name": {"page": 1, "x": 72, "y": 200, "w": 300, "h": 20, "size": 11}
        }},
}


def validate_configs():
    """Check all configured states have the required files."""
    import os
    d = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")
    for code, cfg in STATE_CONFIGS.items():
        # Check answer form
        af = cfg.get("answer_form")
        if af:
            path = os.path.join(d, af)
            if not os.path.exists(path):
                print(f"  ❌ {code}: Missing answer form: {af}")
            else:
                print(f"  ✅ {code}: {af}")

        # Check fee waiver
        fw = cfg.get("fee_waiver_form")
        if fw:
            path = os.path.join(d, fw)
            if not os.path.exists(path):
                print(f"  ❌ {code}: Missing fee waiver: {fw}")


if __name__ == "__main__":
    print("Validating state configs...\n")
    validate_configs()
