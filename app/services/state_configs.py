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
            "monthly_gross_income": "User.SelfTotalNet",
            "phone": "User.PetitionerTelephone",
            "printed_name": "User.PrintNamePetitioner",
            "receives_public_benefits": "User.CB02",
            "receives_snap": "User.SNAP",
            "receives_ssi": "User.SSI",
            "receives_tanf": "User.TANF",
            "total_assets": "User.SelfTotalAssets",
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
        "answer_form": "ga_dispossessory_answer.pdf",
        "fee_waiver_form": "ga_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Magistrate Court",
        "strip_dollar_signs": True,
        "field_mapping": {
            "date": "Date.CurrentDate.SlashMDY",
            "county": "County.Selection",
            "case_number": "CaseNumber",
            "full_name": "Defendant.SEQ001.Name.Full",
            "address": "Defendant.SEQ001.HomeAddress.Street",
            "city_state_zip": "Defendant.SEQ001.HomeAddress.CityStateZip",
            "landlord_name": "Plaintiff.SEQ001.Name.Full",
            "landlord_street": "Plaintiff.SEQ001.HomeAddress.Street",
            "landlord_city_state_zip": "Plaintiff.SEQ001.HomeAddress.CityStateZip",
            "plaintiff_2": "Plaintiff.SEQ002.Name.Full",
            "defendant_2": "Defendant.SEQ002.Name.Full",
            "full_address": "Defendant.SEQ001.HomeAddress.Full",
            "reduced_rent_amount": "Property.ReducedRentAmt",
            "reduced_rent_months": "Property.ReducedRentNumberMonths",
        },
        "static_values": {
            "IsDefendant": "Yes",
            "Plaintiff.SEQ002.Name.Full": "",
            "Defendant.SEQ002.Name.Full": "",
            "Check Box61": "Yes",
            # Real-estate asset "Address" (fee waiver p4) must NOT receive the
            # tenant's rental address (perjury hazard). We don't collect a real
            # estate address, so leave it blank.
            "Address": "",
            # Uniform IFP Affidavit (fee waiver) static overrides.
            "Deputy Clerk of Magistrate Court": "Fulton County Magistrate",
            "Check Box63": "Yes",  # Marital status: Single
            "Check Box21": "Yes",  # AFDC: No
            "Check Box33": "Yes",  # Public housing: No
            "Check Box59": "Yes",  # Valuable personal property: No
            "Check Box2": "Yes",   # Extraordinary medical expenses: No
            "Check Box4": "Yes",   # Other circumstances: No
        },
        "field_rect_overrides": {
            "fee_waiver_form": {
                "COURT OF": {"text_fontsize": 9},
            },
            "answer_form": {
                # Native "additional reasons" widgets ship ~5.6pt wide in the
                # bottom margin; widen them to the printed blank line.
                "Answer.AdditionalReasons": {"x1": 493, "text_fontsize": 9},
                "CounterClaim.AdditionalReasons": {"x1": 493, "text_fontsize": 9},
            },
        },
        "fee_waiver_checkbox_map": {
            "Check Box24": ["receives_tanf"],
            "Check Box25": ["receives_tanf"],
            "Check Box26": ["receives_snap"],
            "Check Box27": ["receives_snap"],
            "Check Box30": ["receives_medicaid"],
            "Check Box31": ["receives_medicaid"],
            "Check Box36": ["employment_income"],
            "Check Box37": ["employment_income"],
            "Check Box38": ["other_income"],
            "Check Box39": ["other_income"],
        },
        "defense_options": [
            {"key": "def_not_owner", "label": "No landlord-tenant relationship", "field": "NoLTRel"},
            {"key": "def_bad_notice", "label": "Improper notice / no proper demand", "field": "Reason.NoNotice"},
            {"key": "def_bad_notice", "label": "Terminated without valid reason", "field": "Reason.Invalid"},
            {"key": "def_amount", "label": "Do not owe any rent", "field": "Reason.NoRentDue"},
            {"key": "def_attempted_pay", "label": "Offered to pay but landlord refused", "field": "Reason.OfferedToPay"},
            {"key": "def_attempted_pay", "label": "Landlord refused payment with costs", "field": "Reason.LandlordRefusePayment"},
            {"key": "def_repairs", "label": "Landlord failed to repair property", "field": "Reason.FailedToRepair"},
            {"key": "def_not_owner", "label": "Landlord not entitled to evict", "field": "Reason.LandlordNotEntitled"},
            {"key": "def_repairs", "label": "Landlord failed to repair (counterclaim)", "field": "FailedToRepair"},
            {"key": "def_corrected", "label": "Defendant made repairs", "field": "Defendant.DidMakeRepairs"},
            {"key": "def_paid", "label": "Landlord owes money", "field": "DoesOweMoney"},
        ],
        "notes": "GA MAG 30-03 Dispossessory Answer — statewide form from Council of Magistrate Court Judges. 36 fillable fields, single page. Accepted in all 159 GA counties. Filing procedures vary by county (e-filing vs mail vs in-person).",
        "fee_waiver_mapping": {
            "address": "2 Current Address",
            "case_number": "FILE NO",
            "checking_balance": "What is the current balance in your account",
            "city": "City",
            "court_level": "COURT OF",
            "county": "COUNTY",
            "debt_payments": "Total_2",
            "email": "4 Email Address",
            "employment_income": "TOTAL AMOUNT OF INCOME RECEIVED PER MONTH IF ANY",
            "full_name": "1 Name",
            "household_children": "2 How many people not including yourself do you currently support",
            "landlord_name": "undefined",
            "phone": "3 Best Telephone Number to Reach You",
            "property_zip": "Zip Code",
            "real_estate_loan_owed": "How much do you owe on the property mortgage balance",
            "real_estate_value": "What is the approximate value of the property",
            "savings_balance": "What is the current balance in your account_2",
            "state": "State",
            "vehicle_make_model": "Make",
            "vehicle_value": "What is the approximate value of the vehicle",
        },
        "fee_waiver_name_fields": [
            "undefined_3",
            "do hereby swear",
            "Print name",
            "1 Name",
        ],
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
            "case_number": {"page": 1, "x": 210, "y": 60, "w": 110, "h": 12, "size": 9},
            "full_name": {"page": 1, "x": 165, "y": 233, "w": 180, "h": 10, "size": 10}
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
            "address": "Last - Street Address",
            "case_number": "4 - Case Number",
            "cash_on_hand": "87 - Value",
            "child_care_expense": "74 - Childcare Total",
            "child_support_income": "23 - Child Support Total",
            "county": "1 - County",
            "email": "Last - Email",
            "employment_income": "19 - My Employment Total",
            "food_expense": "68 - Food Total",
            "full_name": "6 - Your Name",
            "household_adults": "8 - # of Adults",
            "household_children": "9 - Number of Children Under 18",
            "medical_expense": "70 - Medical Total",
            "pension_income": "27 - Pension Total",
            "phone": "Last - Telephone",
            "printed_name": "Last - Print Name",
            "real_estate_loan_owed": "90 - Total Home Mortgage",
            "real_estate_value": "89 - Value",
            "receives_county_assistance": "12 - GA",
            "receives_snap": "13 - SNAP",
            "receives_ssi": "10 - SSI",
            "receives_tanf": "14 - TANF",
            "rent_or_mortgage": "60 - Rent Total",
            "social_security_income": "21 - Social Security Total",
            "transportation_expense": "72 - Vehicle Total",
            "unemployment_income": "25 - Unemployment Total",
            "utilities_expense": "66 - Utilities Total",
            "vehicle_value": "94 - Value",
        },
        "has_fillable_fields": True,
        "court_type": "Circuit Court",
        "skip_financial_when_categorical": True,
        "populate_signature_fields": True,
        "field_mapping": {
            "county": "1 - County",
            "full_name": "5 - Defendants (First, middle, last name)",
            "landlord_name": "2 - Plaintiff Name (First, Middle, Last)",
            "case_number": "9 - Case Number",
            "property_address": "10 - Property Address",
            # Page 4 primary certification (735 ILCS 5/1-109)
            "printed_name": "117",
            "address": "120",
            "city_state_zip": "121",
            "phone": "118",
            "email": "122",
            # Page 5 proof of delivery (recipient = landlord)
            "plaintiff": "1A - Full Name of Party - Page 4",
            "landlord_address": "1A - Full Address of Party - Page 4",
            # Page 6 proof of delivery signature block (filer)
            "proof_signature": "E - Signature",
            "proof_name": "G - Name",
            "proof_phone": "I - Telephone",
            "proof_city_state_zip": "H - City, State, ZIP",
            "proof_email": "J - Email",
        },
        "static_values": {
            "11 - Checkboxes": "I deny the claims made by the Plaintiff (landlord) in their Eviction Complaint ",
            "3 - Plaintiff Name (First, Middle, Last)": "",
            "4 - Plaintiff Name (First, Middle, Last)": "",
            "6 - Defendants (First, middle, last name)": "",
            "7 - Defendants (First, middle, last name)": "",
            "116": "/s/",
            "1A - Email of Party - Page 4": "",
            "4 - Address or Intersection": "",
            "4 - Delivery Address": "",
            "4B - Full Name of Party - Page 4": "",
            "4B - Full Address of Party - Page 4": "",
            "4B - Email of Party - Page 4": "",
            "4B - Address or Intersection": "",
            "54 - Date": "",
            "55 - Date": "",
            "57 - Date": "",
            "58 - Date": "",
            "60 - Date": "",
            "61 - Date": "",
            "74.1 - Date": "",
            "74.2 - Date": "",
            "74.3 - Date": "",
            "78 - Date": "",
            "79 - Date": "",
            "85 - Date": "",
            "4 - Document Date": "",
            "4B - Document Date": "",
            "Last - Lawyer Email": "",
            "Last - Lawyer Address": "",
            "Last - Completing this form myself checkbox": "Yes",
            "Last - Lawyer completing the form checkbox": "Off",
        },
        "strip_dollar_signs": True,
        "defense_options": [
            # Section 2 affirmative defenses (pages 2-3). Section 1a General Denial
            # (checked via static_values) handles the complaint paragraphs, so the
            # admit/deny/do-not-know triads stay blank.
            {"key": "def_bad_notice", "label": "No/Improper Notice", "field": "43 - Checkbox"},
            {"key": "def_corrected", "label": "Cure lease violation", "field": "48 - Checkbox"},
            {"key": "def_repairs", "label": "Bad Property Conditions", "field": "52 - Checkbox"},
            {"key": "def_retaliation", "label": "Retaliation", "field": "63 - Checkbox"},
            {"key": "def_waived", "label": "Waiver/Accepted rent", "field": "77 - Checkbox"},
            {"key": "def_attempted_pay", "label": "Refusal to accept rent payment", "field": "84 - Checkbox"},
            {"key": "def_other", "label": "Other affirmative defense", "field": "90 - Checkbox"},
        ],
        "notes": "IL Circuit Court eviction answer — statewide form with 189 field widgets across 6 pages. Cook County has preferred local forms but Illinois law does not mandate a county-specific answer form.",
        "county_form_overrides": {},
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
            "full_address": "topmostSubform[0].Page1[0].ADDRAPP[0]",
            "case_name": "NAMECASE[0]",
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
            "total_monthly_income": "TOTALMONTHLYINCOME",
            "equity_real_estate": "EQUITYRE",
            "equity_vehicle": "EQUITYMV",
            "equity_other_property": "EQUITYOPP",
            "total_assets_equity": "TOTALASSETS",
            "total_debt_owed": "DEBTOWEDTOTAL",
            "transportation_expense": "ME4",
            "utilities_expense": "ME2",
            "vehicle_loan_owed": "MVLOANBAL",
            "vehicle_value": "MVEV",
        },
        "has_fillable_fields": True,
        "court_type": "Housing Court / Superior Court",
        "field_mapping": {
            "case_name": "CASE[0]",
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
        "static_values": {
            # Part 1 — deny (Disagree) every complaint paragraph 1-8.
            "PARA1[1]": "Yes", "PARA2[1]": "Yes", "PARA3[1]": "Yes", "PARA4[1]": "Yes",
            "PARA5[1]": "Yes", "PARA6[1]": "Yes", "PARA7[1]": "Yes", "PARA8[1]": "Yes",
            # Part 2e — notification recipient (the landlord).
            "NOTE[0]": "Yes",
            # Fee waiver (JD-CV-120) — Housing Session + Housing case type
            # (Summary Process actions are Housing Session, not Small Claims).
            "topmostSubform[0].Page1[0].COURT[0]": "Off",  # uncheck Judicial District
            "topmostSubform[0].Page1[0].COURT[1]": "2",    # check Housing Session
            "topmostSubform[0].Page1[0].TYPE[0]": "Off",   # uncheck Civil
            "topmostSubform[0].Page1[0].TYPE[1]": "Off",   # uncheck Small claims
            "topmostSubform[0].Page1[0].TYPE[2]": "4",     # check Housing (Landlord-Tenant)
            "topmostSubform[0].Page1[0].FILING[0]": "Yes", # filing fee
        },
        "defense_details": [
            {"key": "def_repairs", "field": "CODEVIOLA[0]"},
        ],
        "notes": "CT JD-HM-5 form — 62 fillable fields but NO defendant name/address field (form assumes case caption provides it). Tenant data (name, address, phone) uses overlay positions. Landlord info, docket number, and defense checkboxes use fillable fields (full XFA dotted paths).",
    },

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
            "monthly_gross_income": "in the amount of",
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
            "county": "County",
            "full_name": "Name",
            "address": "4.6",
            "city": "4.7",
            "state": "4.8",
            "zip": "4.9",
            "phone": "Phone",
            "email": "Email",
            "household_size": "8A.0",
            "employment_income": "9A.1",
            "unemployment_income": "9A.3",
            "self_employment_income": "9A.6B",
            "rent_or_mortgage": "9B.1",
            "food_expense": "9B.2",
            "utilities_expense": "9B.3",
            "child_care_expense": "9B.4",
            "medical_expense": "9B.5",
            "transportation_expense": "9B.6",
            "debt_payments": "9B.7",
            "total_monthly_expenses": "9B.8",
            "cash_on_hand": "10A.1",
            "savings_balance": "10A.2A",
            "checking_balance": "10A.3A",
            "vehicle_value": "10B.1A",
            "vehicle_make_model": "10B.1B",
            "vehicle_loan_owed": "10B.1C",
            "real_estate_value": "10B.2A",
            "real_estate_loan_owed": "10B.2C",
            "receives_blind_aid": "6.1",
            "receives_oap": "6.2",
            "receives_ssi": "6.3",
            "receives_tanf": "6.4",
            "receives_snap": "6.5",
            "receives_and": "6.6",
            "date": "Sig1_Date",
            "printed_name": "Name",
        },
        "has_fillable_fields": True,
        "court_type": "County Court",
        "skip_financial_when_categorical": True,
        "bind_late_fee_defense": True,
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
        
            "cos_mail": "CoS_Mail",
            "defense_narrative": "8.0",
            "day": "Sig1_Date",
            "month": "Sig1_Month",
            "year": "Sig1_Year",
            "property_city": "Sig1_City",
            "state_code": "Sig1_State",
            "defendant_name": "Sig1_Name",
            "printed_name": "Name"},
        "radio_selections": {
            "Group1.1": {"value": "county court"},
            "Group6.0": {"any_financial": ["receives_ssi", "receives_tanf", "receives_snap"], "yes": "yes", "no": "no"},
            "Group_CoS": {"value": "regular mail"},
            "Group7.1": {"skip_when_categorical": True, "data": "owns_real_estate", "yes": "own", "no": "rent"},
            "Group7.3": {"skip_when_categorical": True, "data": "employment_income", "yes": "yes", "no": "no"},
            "Group7A.0": {"any_defense": ["def_paid", "def_attempted_pay", "def_partial_pay", "def_repairs"], "yes": "yes", "no": "no"},
            "Group7B.0": {"any_defense": ["def_not_violate", "def_not_repeat", "def_domestic_violence"], "yes": "yes", "no": "no"},
            "Group7C.0": {"any_defense": ["def_no_substantial_violation"], "yes": "yes", "no": "no"},
            "Group7D.0": {"any_defense": ["def_retaliation", "def_no_fault_just_cause"], "yes": "no", "no": "yes"},
        },
        "defense_options": [
            # Section 7A — Non-Payment Defenses
            {"key": "def_paid", "label": "I paid all rent owed", "field": "7A.1"},
            {"key": "def_attempted_pay", "label": "I tried to pay but landlord refused", "field": "7A.2"},
            {"key": "def_partial_pay", "label": "I paid partial rent after demand", "field": "7A.3"},
            {"key": "def_repairs", "label": "Warranty of Habitability (Unfixed Repairs)", "field": "7A.4"},
            # Section 7B — Lease Violation Defenses
            {"key": "def_not_violate", "label": "Did not violate material lease condition", "field": "7B.1"},
            {"key": "def_not_repeat", "label": "Did not repeat alleged violation", "field": "7B.2"},
            {"key": "def_domestic_violence", "label": "Violation resulted from domestic violence", "field": "7B.3"},
            # Section 7C — Substantial Violation
            {"key": "def_no_substantial_violation", "label": "Did not commit substantial violation", "field": "7C.1"},
            # Section 7D — Retaliation / Just Cause
            {"key": "def_retaliation", "label": "Retaliatory eviction", "field": "7D.1"},
            {"key": "def_no_fault_just_cause", "label": "Landlord lacked just cause for non-renewal", "field": "7D.2"},
            # Section 7E — Other Defenses
            {"key": "def_unlawful_fees", "label": "Landlord demands unallowed fees under lease", "field": "7E.1"},
            {"key": "def_amount", "label": "Illegal or unenforceable late fees (C.R.S. 38-12-105)", "field": "7E.2"},
            {"key": "def_bad_notice", "label": "Improper notice / cure period (5-10 days)", "field": "7E.3"},
        ],
        "notes": "CO JDF 103 — 6 pages, 57 fillable fields. Statewide except Denver County Court which requires its own form.",
        "county_form_overrides": {
            "Denver": {
                "note": "Denver County Court DCC CP No. 3 Answer Under Simplified Civil Procedure — 2 pages, overlay. In-person/remote election, narrative defenses.",
                "answer_form": "co_denver_answer.pdf",
                "has_fillable_fields": False,
                "overlay_positions": {
                    "plaintiff_name": {"page": 1, "x": 125, "y": 125, "w": 340, "h": 16, "size": 11},
                    "defendant_name": {"page": 1, "x": 138, "y": 162, "w": 270, "h": 16, "size": 11},
                    "party_info": {"page": 1, "x": 54, "y": 195, "w": 300, "h": 32, "size": 9},
                    "phone": {"page": 1, "x": 138, "y": 230, "w": 95, "h": 11, "size": 9},
                    "email": {"page": 1, "x": 231, "y": 230, "w": 150, "h": 11, "size": 9},
                    "case_number": {"page": 1, "x": 460, "y": 184, "w": 95, "h": 12, "size": 10},
                    "printed_name": {"page": 1, "x": 140, "y": 293, "w": 230, "h": 14, "size": 11},
                    "defense_narrative": {"page": 1, "x": 54, "y": 475, "w": 504, "h": 130, "size": 8.5},
                    "signature": {"page": 2, "x": 60, "y": 458, "w": 250, "h": 20, "size": 11},
                    "property_address": {"page": 2, "x": 190, "y": 500, "w": 360, "h": 14, "size": 10},
                    "phone_bottom": {"page": 2, "x": 210, "y": 523, "w": 200, "h": 14, "size": 10},
                    "checkbox_hearing_in_person": {"page": 1, "x": 241, "y": 340, "w": 14, "h": 14},
                    "checkbox_hearing_remote": {"page": 1, "x": 297, "y": 340, "w": 14, "h": 14},
                    "checkbox_trial_to_court": {"page": 2, "x": 72, "y": 350, "w": 14, "h": 14},
                    "checkbox_trial_jury": {"page": 2, "x": 72, "y": 366, "w": 14, "h": 14},
                    "checkbox_cos_mail": {"page": 2, "x": 405, "y": 605, "w": 14, "h": 14},
                    "cos_date": {"page": 2, "x": 188, "y": 582, "w": 344, "h": 11, "size": 9},
                    "cos_recipient": {"page": 2, "x": 279, "y": 606, "w": 201, "h": 11, "size": 9},
                    "cos_address": {"page": 2, "x": 54, "y": 641, "w": 183, "h": 11, "size": 9},
                },
            },
        },
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
            "rent_or_mortgage": "Monthly Rent",
            "ssi_income": "SSI Support",
            "total_assets": "Total Value of Assets",
            "total_monthly_expenses": "Total Monthly Expenses",
            "transportation_expense": "Transportation",
            "unemployment_income": "Unemployment Benefits",
            "utilities_expense": "Electricity",
            "is_employed": "Employed - Yes",
            "has_bank_account": "Bank Account - Yes",
            "is_single": "Household - Single",
            "vehicle_loan_owed": "Balance Owed - Auto",
            "vehicle_value": "Value of Interest - Auto",
            "zip": "Zip Code",
            # Page 3: Mover's Affidavit
            "county_mover": "Mover's Affidavit State of Louisiana Parish Of",
            "full_name_mover": "Mover's Affidavit Before Me Appeared",
            # Page 4: Third Party Affidavit & Order
            "county_tp": "Third Party Affidavit State of Louisiana Parish Of",
            "full_name_tp": "Third Party Affidavit He/She Knows",
            "full_name_order": "Order Name",
        },
        "fee_waiver_name_fields": [
            "Your Full Name",
            "Mover's Affidavit Before Me Appeared",
            "Third Party Affidavit He/She Knows",
            "Order Name",
        ],
        "strip_dollar_signs": True,
        "has_fillable_fields": True,
        "court_type": "District Court / City Court",
        "field_mapping": {},
        "overlay_positions": {
            "landlord_name": {"page": 3, "x": 150, "y": 85, "w": 230, "h": 16, "size": 10},
            "case_number": {"page": 3, "x": 390, "y": 87, "w": 180, "h": 16, "size": 10},
            "full_name": {"page": 3, "x": 150, "y": 189, "w": 230, "h": 16, "size": 10},
            "court_name": {"page": 3, "x": 460, "y": 191, "w": 180, "h": 16, "size": 9},
            # Page 11: Section 5 notary verification block (La. C.C.P. art. 4735).
            "full_name_p11": {"page": 11, "x": 75, "y": 226, "w": 210, "h": 16, "size": 11},
            "date_p11": {"page": 11, "x": 75, "y": 366, "w": 210, "h": 16, "size": 11},
        },
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
            {"key": "def_late_payments", "label": "Landlord accepted late payments before", "field": "My landlord has accepted late payments in the past I have proof of my late"},
            {"key": "def_not_violate_lease", "label": "I did not commit the lease violations", "field": "I did not commit the lease violations stated by my landlord"},
            {"key": "def_disability", "label": "Violation related to disability", "field": "The alleged violation of my lease is related to my physical or mental disability and I"},
            {"key": "def_repairs", "label": "Used rent money for repairs landlord ignored", "field": "I used my rent money to make repairs that my landlord did not take care of"},
            {"key": "def_domestic_violence", "label": "Eviction related to domestic violence", "field": "My eviction is related to domestic violence"},
            {"key": "def_other_defenses", "label": "Other defenses", "field": "I have some other defenses"},
            {"key": "def_no_notice", "label": "Did not receive Notice to Vacate", "field": "The landlord did not issue a written Notice to Vacate that explains the reason for the"},
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
            "signature": {"page": 1, "x": 143, "y": 550, "w": 200, "h": 20, "size": 10},
            "defense_narrative": {"page": 1, "x": 72, "y": 370, "w": 450, "h": 500, "size": 7}},

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
            "case_number": {"page": 1, "x": 488, "y": 68, "w": 75, "h": 12, "size": 10},
            "county": {"page": 1, "x": 36, "y": 52, "w": 80, "h": 16, "size": 10},
            "full_name": {"page": 1, "x": 95, "y": 194, "w": 130, "h": 12, "size": 10},
            "address": {"page": 1, "x": 395, "y": 194, "w": 140, "h": 12, "size": 10},
            "phone": {"page": 1, "x": 130, "y": 205, "w": 120, "h": 12, "size": 10}
        }},

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
            "court_level": "IN THE",
            "court_caption_county": "COURT",
            "date": "day of",
            "full_name": "IN RE PETITION OF",
            "cash_on_hand": "has the sum of",
        },
        "fee_waiver_name_fields": ["I", "Petitioner"],
        "fee_waiver_checkbox_map": {
            "Check Box1": ["employment_income"],
            "Check Box3": ["self_employment_income"],
            "Check Box5": ["rental_income", "interest_income", "dividend_income"],
            "Check Box7": ["pension_income"],
            "Check Box9": ["gift_income", "inheritance_income"],
            "Check Box11": ["other_income", "unemployment_income", "social_security_income", "child_support_income", "alimony_income", "disability_income"],
            "Check Box13": ["checking_balance", "savings_balance", "cash_on_hand"],
            "Check Box15": ["vehicle_make_model", "real_estate_value", "other_assets_value"],
            "Check Box17": ["household_children"],
        },
        "has_fillable_fields": False,
        "court_type": "Circuit Court",
        "overlay_positions": {
            "county": {"page": 6, "x": 242, "y": 166, "w": 145, "h": 15, "size": 11},
            "plaintiff_name": {"page": 6, "x": 67, "y": 204, "w": 333, "h": 16, "size": 11},
            "case_number": {"page": 6, "x": 318, "y": 249, "w": 88, "h": 15, "size": 11},
            "defendant_name": {"page": 6, "x": 67, "y": 292, "w": 333, "h": 16, "size": 11},
            "defendant_appearance": {"page": 6, "x": 299, "y": 375, "w": 235, "h": 16, "size": 10},
            "response_narrative": {"page": 7, "x": 90, "y": 85, "w": 420, "h": 40, "size": 9},
            "defense_narrative": {"page": 8, "x": 90, "y": 350, "w": 420, "h": 120, "size": 9},
            "counterclaim_narrative": {"page": 8, "x": 65, "y": 590, "w": 500, "h": 130, "size": 9},
            "signature": {"page": 9, "x": 408, "y": 685, "w": 92, "h": 20, "size": 10},
            "address": {"page": 10, "x": 310, "y": 108, "w": 230, "h": 16, "size": 10},
            "phone": {"page": 10, "x": 358, "y": 138, "w": 150, "h": 16, "size": 10},
            "date": {"page": 10, "x": 355, "y": 496, "w": 145, "h": 12, "size": 10},
            "full_name": {"page": 10, "x": 95, "y": 243, "w": 200, "h": 16, "size": 11},
            "landlord_name": {"page": 10, "x": 70, "y": 293, "w": 350, "h": 16, "size": 10},
            "landlord_address": {"page": 10, "x": 70, "y": 330, "w": 350, "h": 14, "size": 10},
        },
        "notes": "AR Answer, Counterclaim & Objection to Writ — statewide-compliant combined document from Arkansas Justice. Covers both deadlines: 5-day objection to possession AND 30-day answer to complaint. 75/75 counties. Court caption dynamically filled with county and circuit court.",
    },

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
            "county": {"page": 1, "x": 130, "y": 110, "w": 190, "h": 16, "size": 11},
            "case_number": {"page": 1, "x": 460, "y": 129, "w": 110, "h": 16, "size": 10},
            "landlord_name": {"page": 1, "x": 76, "y": 186, "w": 235, "h": 16, "size": 11},
            "full_name": {"page": 1, "x": 76, "y": 275, "w": 235, "h": 16, "size": 11},
            "address": {"page": 1, "x": 76, "y": 323, "w": 235, "h": 16, "size": 11},
            # Form HOU202 defense checkboxes (Q5/Q6/Q9/Q10)
            "def_amount": {"page": 2, "x": 95, "y": 393, "w": 14, "h": 14},
            "def_bad_notice": {"page": 2, "x": 95, "y": 527, "w": 14, "h": 14},
            "def_repairs": {"page": 3, "x": 95, "y": 162, "w": 14, "h": 14},
            "def_other": {"page": 3, "x": 95, "y": 136, "w": 14, "h": 14},
            # Defense explanations routed to their matching items
            "explanation_def_amount": {"page": 2, "x": 108, "y": 425, "w": 440, "h": 80, "size": 8},
            "explanation_def_bad_notice": {"page": 2, "x": 108, "y": 552, "w": 440, "h": 80, "size": 8},
            "explanation_def_repairs": {"page": 3, "x": 108, "y": 195, "w": 440, "h": 80, "size": 8},
            # Page 4: verification + signature block + contact info
            "date": {"page": 4, "x": 110, "y": 229, "w": 80, "h": 14, "size": 10},
            "printed_name": {"page": 4, "x": 330, "y": 289, "w": 210, "h": 14, "size": 10},
            "property_address": {"page": 4, "x": 340, "y": 311, "w": 200, "h": 14, "size": 10},
            "city_state_zip": {"page": 4, "x": 370, "y": 333, "w": 170, "h": 14, "size": 10},
            "phone": {"page": 4, "x": 350, "y": 354, "w": 190, "h": 14, "size": 10},
            "email": {"page": 4, "x": 370, "y": 377, "w": 170, "h": 14, "size": 10},
        },
        "notes": "MN HOU202 Housing Court Eviction Answer — scanned PDF. Data fields on page 1 via overlay; defense explanations routed to items 5/6/9; verification/contact block on page 4. OCR-verified at 600 DPI.",
        "fee_waiver_checkbox_overrides": {
            "cb_1_0": False,   # "do not receive public assistance" — off
            "cb_1_1": True,    # "I receive public assistance" — on
            "cb_1_2": True,    # "a. under one or more..." — on
            "cb_1_6": "receives_snap",      # SNAP / Food Stamps
            "cb_1_8": "receives_medicaid",  # Medical Assistance
            "cb_1_12": False,  # SSI — off
        },
    
        "fee_waiver_overlay": {
            "county": {"page": 1, "x": 132, "y": 116, "w": 150, "h": 16, "size": 10},
            "case_number": {"page": 1, "x": 408, "y": 116, "w": 132, "h": 16, "size": 10},
            "plaintiff_name": {"page": 1, "x": 170, "y": 195, "w": 230, "h": 14, "size": 11},
            "judicial_district": {"page": 1, "x": 150, "y": 142, "w": 100, "h": 14, "size": 10},
            "case_type": {"page": 1, "x": 400, "y": 142, "w": 120, "h": 14, "size": 10},
            "full_name": {"page": 1, "x": 172, "y": 248, "w": 230, "h": 16, "size": 11},
            "date": {"page": 6, "x": 110, "y": 332, "w": 80, "h": 14, "size": 10},
            "county_page6": {"page": 6, "x": 230, "y": 340, "w": 180, "h": 16, "size": 10},
            "printed_name": {"page": 6, "x": 115, "y": 380, "w": 200, "h": 14, "size": 10},
            "property_address": {"page": 6, "x": 125, "y": 396, "w": 240, "h": 14, "size": 10},
            "city_state_zip": {"page": 6, "x": 155, "y": 412, "w": 220, "h": 14, "size": 10},
            "phone": {"page": 6, "x": 118, "y": 427, "w": 180, "h": 14, "size": 10},
            "email": {"page": 6, "x": 112, "y": 443, "w": 240, "h": 14, "size": 10},
        }},

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
            "county": {"page": 1, "x": 280, "y": 88, "w": 130, "h": 16, "size": 11},
            "case_number": {"page": 1, "x": 400, "y": 143, "w": 160, "h": 16, "size": 11},
            "landlord_name": {"page": 1, "x": 350, "y": 157, "w": 200, "h": 16, "size": 11},
            "full_name": {"page": 1, "x": 350, "y": 226, "w": 200, "h": 16, "size": 11},
            "signature": {"page": 1, "x": 150, "y": 629, "w": 100, "h": 16, "size": 10},
            "printed_name": {"page": 1, "x": 320, "y": 630, "w": 170, "h": 16, "size": 10},
            "date": {"page": 1, "x": 530, "y": 630, "w": 70, "h": 16, "size": 10},
            "address": {"page": 1, "x": 150, "y": 667, "w": 200, "h": 16, "size": 10},
            "phone": {"page": 1, "x": 530, "y": 667, "w": 70, "h": 16, "size": 10},
            "email": {"page": 1, "x": 150, "y": 704, "w": 200, "h": 16, "size": 10},
        },
        "notes": "OR FED Answer — scanned PDF with 10 checkbox defenses (OCR-verified at 600 DPI). Overlay positions for essential fields on page 1 caption area.",
    
        "fee_waiver_overlay": {
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
            "court_name": "ctaddress",
            "date": "Date",
            "full_name": "dname",
            "household_size": "Number in household",
            "judicial_district": "district",
            "landlord_name": "pname",
            "monthly_gross_income": "My Gross Household Income is in Dollars",
            "obligations_description": "Obligations",
            "other_income_description": "My Source Of Income Is",
            "receives_medicaid": "Medicaid",
            "receives_public_benefits": "Option 1 of 2: I Receive Public Assistance Because Of Indigence",
            "receives_snap": "Food Assistance Program ",
            "receives_ssi": "Supplemental Security Income (SSI)",
            "receives_tanf": "Family Independence Program",
        },
        "fee_waiver_name_fields": ["printed"],
        "static_values": {
            "Week and or Two Weeks and or  Month and or Year ": "Month",
        },
        "has_fillable_fields": True,
        "court_type": "District Court",
        "populate_signature_dates": True,
        "field_mapping": {
            "judicial_district": "Judicial district",
            "case_number": "Case number",
            "court_name": "Court address",
            "defendant_composite": "Defendant name, address, and telephone number",
            "plaintiff_composite": "Plaintiff name, address, and telephone number",
            "date": "Date",
            "cert_date": "Enter date",
            "printed_name": "Enter defendant or attorney signature",
        },
        "defense_options": [
            {"key": "def_jury_trial", "label": "I demand a jury trial", "field": "1. I demand a jury trial"},
            {"key": "def_not_owner", "label": "Plaintiff is not the owner (Item 3)", "field": "disagree 3"},
            {"key": "def_amount", "label": "Dispute rent amount claimed (Item 5)", "field": "disagree 5"},
            {"key": "def_regulated_housing", "label": "Dispute regulated housing status (Item 6)", "field": "disagree 6"},
            {"key": "def_repairs", "label": "Failure to repair / habitability (Item 7 - MCL 554.139)", "field": "disagree 7"},
            {"key": "def_amount", "label": "Dispute non-compliance with demand (Item 8)", "field": "8. disagree that"},
            {"key": "def_amount", "label": "Dispute judgment & costs requested (Item 9)", "field": "9. disagree"},
        ],
        "defense_details": [
            {"key": "def_not_owner", "field": "details 3"},
            {"key": "def_amount", "field": "details 5"},
            {"key": "def_repairs", "field": "details 7"},
        ],
        "defense_details_aggregate": {
            "11. Other statements related to this case are: Use a separate sheet of paper if needed": ["def_retaliation", "def_bad_notice", "def_fair_housing", "def_other"],
        },
        "notes": "MI DC 111a Answer — Nonpayment of Rent. 48 fields across 2 pages with agree/disagree paragraph structure. Defendant and plaintiff fields are composite (name+address+phone in one field).",
    },

    # ══════════════════════════════════════════
    # NEW MEXICO — Form 4-907 Answer to Petition for Restitution
    # Statewide form for ALL 33 NM counties (Magistrate, Metropolitan, District courts)
    # Scanned/non-fillable — uses overlay for all fields
    # ══════════════════════════════════════════
    "NM": {
        "name": "New Mexico",
        "answer_form": "nm_form_4-907.pdf",
        "fee_waiver_form": "nm_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Magistrate Court",
        "overlay_positions": {
            # Page 0 — Court header
            "court_type": {"page": 1, "x": 90, "y": 114, "w": 96, "h": 16, "size": 10},
            "county": {"page": 1, "x": 90, "y": 128, "w": 96, "h": 16, "size": 10},
            "case_number": {"page": 1, "x": 462, "y": 156, "w": 120, "h": 16, "size": 10},
            # Party names
            "defendant_name": {"page": 1, "x": 90, "y": 240, "w": 432, "h": 18, "size": 11},
            "plaintiff_name": {"page": 1, "x": 90, "y": 184, "w": 432, "h": 18, "size": 11},
            # Defense narratives — filled into the blank lines after each "because:"
            "defense_narrative_1": {"page": 1, "x": 370, "y": 340, "w": 152, "h": 14, "size": 8},
            "defense_narrative_2": {"page": 1, "x": 370, "y": 394, "w": 152, "h": 14, "size": 8},
            "defense_narrative_3": {"page": 1, "x": 370, "y": 436, "w": 152, "h": 14, "size": 8},
            "defense_narrative_4": {"page": 1, "x": 370, "y": 492, "w": 152, "h": 14, "size": 8},
            # Signature block
            "signature": {"page": 1, "x": 162, "y": 547, "w": 260, "h": 25, "size": 11},
            "printed_name": {"page": 1, "x": 300, "y": 606, "w": 200, "h": 15, "size": 10},
            "property_address": {"page": 1, "x": 310, "y": 647, "w": 200, "h": 15, "size": 10},
            "city_state_zip": {"page": 1, "x": 385, "y": 689, "w": 150, "h": 15, "size": 10},
            # Page 2 — Telephone
            "phone": {"page": 2, "x": 325, "y": 60, "w": 180, "h": 15, "size": 10},
        },
        "notes": "NM Form 4-907 — statewide for all 33 counties. Works in Magistrate, Metropolitan, and District courts. Narrative-style defenses (write-in).",
        "fee_waiver_overlay": {
            "county": {"page": 1, "x": 300, "y": 120, "w": 200, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 385, "y": 230, "w": 115, "h": 16, "size": 11},
            "date": {"page": 5, "x": 72, "y": 600, "w": 150, "h": 20, "size": 11},
            "full_name": {"page": 1, "x": 72, "y": 200, "w": 300, "h": 20, "size": 11}
        }},

    # ══════════════════════════════════════════
    # MISSOURI — Answer to Rent and Possession Complaint (narrative)
    # GN10 statewide fee waiver (62 fillable fields)
    # ══════════════════════════════════════════
    "MO": {
        "name": "Missouri",
        "answer_form": "mo_eviction_answer.pdf",
        "fee_waiver_form": "mo_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "county": "COUNTY NAME",
            "court_name": "Judge or Division",
            "case_number": "Case Number",
            "landlord_name": "Petitioner Name",
            "landlord_address": "Petitioners AddressTelephone",
            "full_name": "Respondent Name",
            "property_address": "Respondents AddressTelephone",
            "total_dependents": "Number of dependents",
            "employment_income": "Gross Salary",
            "ssi_income": "Public Assistance",
            "pension_income": "Retirement/Pension",
            "social_security_income": "Social Security",
            "child_support_income": "Child Support",
            "alimony_income": "Maintenance - Income",
            "other_income": "Other Income Amount",
            "other_income_description": "Other income to be considered",
            "monthly_gross_income": "Total Monthly Income",
            "rent_or_mortgage": "Mortgage or Rent Payment Amount",
            "utilities_expense": "Utilities Amount",
            "food_expense": "Food Amount",
            "debt_payments": "Payment on Debts and Credit Cards",
            "medical_expense": "Medical Expenses",
            "total_monthly_expenses": "Total Monthly Expenses",
            "cash_on_hand": "Cash on Hand",
            "checking_balance": "Checking Account",
            "savings_balance": "Savings Account",
            "vehicle_value": "Value of Automobiles",
            "real_estate_loan_owed": "Home Loan Balance",
            "vehicle_loan_owed": "Automobile Loan",
            "total_assets": "Total Assets",
            "total_debts": "Total Debts",
        },
        "has_fillable_fields": True,
        "court_type": "Associate Circuit Court",
        "field_mapping": {
            "division": "division",
        },
        "defense_options": [
            {"key": "def_repairs", "label": "The landlord failed to make necessary repairs", "field": "defense_repairs"},
            {"key": "def_amount", "label": "I dispute the amount of rent claimed", "field": "defense_amount"},
            {"key": "def_attempted_pay", "label": "I attempted to pay but the landlord refused", "field": "defense_attempted_pay"},
            {"key": "def_paid", "label": "I already paid the rent demanded", "field": "defense_paid"},
            {"key": "def_waived", "label": "The landlord waived or canceled the notice", "field": "defense_waived"},
            {"key": "def_retaliation", "label": "The eviction is retaliatory", "field": "defense_retaliation"},
            {"key": "def_fair_housing", "label": "The eviction violates fair housing law", "field": "defense_discrimination"},
            {"key": "def_accepted_rent", "label": "The landlord accepted rent after notice", "field": "defense_accepted_rent"},
            {"key": "def_corrected", "label": "I already corrected the issue", "field": "defense_corrected"},
            {"key": "def_not_owner", "label": "The person suing me is not the owner", "field": "defense_not_owner"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice", "field": "defense_bad_notice"},
            {"key": "def_other", "label": "Other defenses", "field": "defense_other"},
        ],
        "notes": "MO Rent and Possession answer (narrative) + GN10 statewide fee waiver (62 fillable fields).",
    },

    # ══════════════════════════════════════════
    # KENTUCKY — Answer to Forcible Detainer (narrative)
    # AOC-026 statewide fee waiver (128 fields)
    # ══════════════════════════════════════════
    "KY": {
        "name": "Kentucky",
        "answer_form": "ky_eviction_answer.pdf",
        "fee_waiver_form": "ky_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "case_number": "Case Number",
            "court_name": "Court",
            "county": "County Dropdown",
            "division": "Division",
            "landlord_name": "Plaintiff",
            "full_name": "Defendant",
            "full_name_applicant": "Text Field 6",
            "property_address": "Text Field 7",
            "city_state_zip": "Text Field 8",
            "phone_area_code": "Text Field 10",
            "phone_number_only": "Text Field 11",
            "employment_income": "Text Field 19",
            "social_security_income": "Text Field 32",
            "unemployment_income": "Text Field 34",
            "pension_income": "Text Field 35",
            "child_support_income": "Text Field 36",
            "alimony_income": "Text Field 37",
            "monthly_gross_income": "Text Field 61",
            "rent_or_mortgage": "Text Field 44",
            "utilities_expense": "Text Field 45",
            "food_expense": "Text Field 47",
            "transportation_expense": "Text Field 51",
            "medical_expense": "Text Field 59",
            "total_monthly_expenses": "Text Field 62",
            "cash_on_hand": "Assests 1",
            "checking_balance": "Assests 2",
            "savings_balance": "Assests 3",
            "total_assets": "Assests Total",
            "total_debts": "Debts Total",
            "date": "Text Field 109",
            "printed_name": "Text Field 1010",
        },
        "strip_dollar_signs": True,
        "has_fillable_fields": True,
        "court_type": "District Court",
        "field_mapping": {
            "division": "division",
            "cert_name": "cert_name",
        },
        "defense_options": [
            {"key": "def_repairs", "label": "The landlord failed to make necessary repairs", "field": "defense_repairs"},
            {"key": "def_amount", "label": "I dispute the amount of rent claimed", "field": "defense_amount"},
            {"key": "def_attempted_pay", "label": "I attempted to pay but the landlord refused", "field": "defense_attempted_pay"},
            {"key": "def_paid", "label": "I already paid the rent demanded", "field": "defense_paid"},
            {"key": "def_waived", "label": "The landlord waived or canceled the notice", "field": "defense_waived"},
            {"key": "def_retaliation", "label": "The eviction is retaliatory", "field": "defense_retaliation"},
            {"key": "def_fair_housing", "label": "The eviction violates fair housing law", "field": "defense_discrimination"},
            {"key": "def_accepted_rent", "label": "The landlord accepted rent after notice", "field": "defense_accepted_rent"},
            {"key": "def_corrected", "label": "I already corrected the issue", "field": "defense_corrected"},
            {"key": "def_not_owner", "label": "The person suing me is not the owner", "field": "defense_not_owner"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice", "field": "defense_bad_notice"},
            {"key": "def_other", "label": "Other defenses", "field": "defense_other"},
        ],
        "notes": "KY forcible detainer (hearing-based) + AOC-026 statewide fee waiver (128 fields).",
    },

    # ══════════════════════════════════════════
    # OKLAHOMA — Answer to FED Petition (narrative)
    # Pauper's Affidavit fee waiver
    # ══════════════════════════════════════════
    "OK": {
        "name": "Oklahoma",
        "answer_form": "ok_eviction_answer.pdf",
        "fee_waiver_form": "ok_fee_waiver_fillable.pdf",
        "fee_waiver_mapping": {
            "full_name": "full_name",
            "employment_income": "employment_income",
            "rent_or_mortgage": "rent_or_mortgage",
            "checking_balance": "checking_balance",
            "cash_on_hand": "cash_on_hand",
            "vehicle_value": "vehicle_value",
            "utilities_expense": "utilities_expense",
        },
        "has_fillable_fields": True,
        "court_type": "District Court",
        "field_mapping": {
            "division": "division",
        },
        "defense_options": [
            {"key": "def_repairs", "label": "The landlord failed to make necessary repairs", "field": "defense_repairs"},
            {"key": "def_amount", "label": "I dispute the amount of rent claimed", "field": "defense_amount"},
            {"key": "def_attempted_pay", "label": "I attempted to pay but the landlord refused", "field": "defense_attempted_pay"},
            {"key": "def_paid", "label": "I already paid the rent demanded", "field": "defense_paid"},
            {"key": "def_waived", "label": "The landlord waived or canceled the notice", "field": "defense_waived"},
            {"key": "def_retaliation", "label": "The eviction is retaliatory", "field": "defense_retaliation"},
            {"key": "def_fair_housing", "label": "The eviction violates fair housing law", "field": "defense_discrimination"},
            {"key": "def_accepted_rent", "label": "The landlord accepted rent after notice", "field": "defense_accepted_rent"},
            {"key": "def_corrected", "label": "I already corrected the issue", "field": "defense_corrected"},
            {"key": "def_not_owner", "label": "The person suing me is not the owner", "field": "defense_not_owner"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice", "field": "defense_bad_notice"},
            {"key": "def_other", "label": "Other defenses", "field": "defense_other"},
        ],
        "notes": "OK Forcible Entry and Detainer (narrative answer) + Pauper's Affidavit fee waiver.",
    },

    # ══════════════════════════════════════════
    # INDIANA — Answer to Notice of Claim (narrative)
    # General Fee Waiver Motion and Order (fillable)
    # ══════════════════════════════════════════
    "IN": {
        "name": "Indiana",
        "answer_form": "in_eviction_answer.pdf",
        "fee_waiver_form": "in_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "county": "County",
            "full_name": "Petitioner",
            "landlord_name": "Respondent",
            "household_adults": "HouseholdAdults",
            "household_children": "HouseholdChildren",
            "monthly_gross_income": "CombinedIncome",
            "employment_income": "HourlyWagexMonthlyHours",
            "total_monthly_income": "TotalMonthlyIncome",
            "cash_on_hand": "BankAccount",
            "total_monthly_expenses": "ExpensesTotal",
            "rent_or_mortgage": "MonthlyHousing",
            "utilities_expense": "MonthlyUtilities",
            "food_expense": "MonthlyFood",
            "child_care_expense": "MonthlyChildCare",
            "medical_expense": "MonthlyMedicalBills",
            "transportation_expense": "MonthlyTransportation",
            "other_expenses": "MonthlyOtherExpenses",
            "total_expenses_table": "MonthlyExpensesTotal",
            "unemployment_income": "MonthlyUnemployment",
            "ssi_income": "MonthlySSI/SSD",
            "child_support_income": "MonthlyChildSupportReceived",
            "property_address": "Address",
        },
        "fee_waiver_name_fields": ["Name"],
        "strip_dollar_signs": True,
        "fee_waiver_overlay": {
            "case_number": {"page": 1, "x": 355, "y": 62, "w": 140, "h": 16, "size": 11},
            "date": {"page": 2, "x": 72, "y": 553, "w": 150, "h": 16, "size": 10},
            "case_number_page3": {"page": 3, "x": 335, "y": 100, "w": 160, "h": 16, "size": 10},
        },
        "field_rect_overrides": {
            "fee_waiver_form": {
                "Address": {"y0": 655.0},
            },
        },
        "has_fillable_fields": True,
        "court_type": "Small Claims Court",
        "field_mapping": {
            "division": "division",
        },
        "defense_options": [
            {"key": "def_repairs", "label": "The landlord failed to make necessary repairs", "field": "defense_repairs"},
            {"key": "def_amount", "label": "I dispute the amount of rent claimed", "field": "defense_amount"},
            {"key": "def_attempted_pay", "label": "I attempted to pay but the landlord refused", "field": "defense_attempted_pay"},
            {"key": "def_paid", "label": "I already paid the rent demanded", "field": "defense_paid"},
            {"key": "def_waived", "label": "The landlord waived or canceled the notice", "field": "defense_waived"},
            {"key": "def_retaliation", "label": "The eviction is retaliatory", "field": "defense_retaliation"},
            {"key": "def_fair_housing", "label": "The eviction violates fair housing law", "field": "defense_discrimination"},
            {"key": "def_accepted_rent", "label": "The landlord accepted rent after notice", "field": "defense_accepted_rent"},
            {"key": "def_corrected", "label": "I already corrected the issue", "field": "defense_corrected"},
            {"key": "def_not_owner", "label": "The person suing me is not the owner", "field": "defense_not_owner"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice", "field": "defense_bad_notice"},
            {"key": "def_other", "label": "Other defenses", "field": "defense_other"},
        ],
        "notes": "IN small claims eviction (hearing-based) + General Fee Waiver Motion (fillable, 38 fields).",
    },

    # ══════════════════════════════════════════
    # OHIO — Answer to FED Complaint (narrative)
    # Form 20 Civil Fee Waiver (recreated fillable)
    # ══════════════════════════════════════════
    "OH": {
        "name": "Ohio",
        "answer_form": "oh_eviction_answer.pdf",
        "fee_waiver_form": "oh_fee_waiver.pdf",
        "fee_waiver_mapping": {
            "full_name": "full_name",
            "total_dependents": "total_dependents",
            "employment_income": "employment_income",
            "monthly_gross_income": "monthly_gross_income",
            "cash_on_hand": "cash_on_hand",
            "checking_balance": "checking_balance",
            "rent_or_mortgage": "rent_or_mortgage",
            "utilities_expense": "utilities_expense",
            "food_expense": "food_expense",
            "transportation_expense": "transportation_expense",
            "child_care_expense": "child_care_expense",
            "medical_expense": "medical_expense",
            "debt_payments": "debt_payments",
            "total_monthly_expenses": "total_monthly_expenses",
        },
        "has_fillable_fields": True,
        "court_type": "Municipal Court",
        "field_mapping": {
            "division": "division",
        },
        "field_rect_overrides": {
            # county widget was authored on the "CASE NO." line — move it up to
            # the "COUNTY, OHIO" line (raw pre-flip coords), narrowed so the name
            # fits before the (shifted-right) "COUNTY, OHIO" label.
            "answer_form": {"county": {"x0": 72, "x1": 108, "y0": 66, "y1": 81}},
            # fee-waiver: county field overlaps "OHIO"; printed_name sits on its label.
            "fee_waiver_form": {
                "county": {"x0": 72, "x1": 108},
                "printed_name": {"x0": 420},
            },
        },
        "defense_options": [
            {"key": "def_repairs", "label": "The landlord failed to make necessary repairs", "field": "defense_repairs"},
            {"key": "def_amount", "label": "I dispute the amount of rent claimed", "field": "defense_amount"},
            {"key": "def_attempted_pay", "label": "I attempted to pay but the landlord refused", "field": "defense_attempted_pay"},
            {"key": "def_paid", "label": "I already paid the rent demanded", "field": "defense_paid"},
            {"key": "def_waived", "label": "The landlord waived or canceled the notice", "field": "defense_waived"},
            {"key": "def_retaliation", "label": "The eviction is retaliatory", "field": "defense_retaliation"},
            {"key": "def_fair_housing", "label": "The eviction violates fair housing law", "field": "defense_discrimination"},
            {"key": "def_accepted_rent", "label": "The landlord accepted rent after notice", "field": "defense_accepted_rent"},
            {"key": "def_corrected", "label": "I already corrected the issue", "field": "defense_corrected"},
            {"key": "def_not_owner", "label": "The person suing me is not the owner", "field": "defense_not_owner"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice", "field": "defense_bad_notice"},
            {"key": "def_other", "label": "Other defenses", "field": "defense_other"},
        ],
        "notes": "OH forcible entry and detainer (narrative answer) + Form 20 Civil Fee Waiver (recreated fillable).",
    },
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
