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
        "has_fillable_fields": True,
        "court_type": "General District Court",
        "field_mapping": {
            "full_name": "User.Defendant",
            "phone": "User.PhoneName2",
            "address": "User.AddressName2",
            "email": "User.CaseNo",
            "landlord_name": "User.Plaintiff",
            "landlord_address": "User.CourtAddress",
            "case_number": "User.CaseNo",
            "court_name": "User.Court",
            "trial_date": "User.TrialDate",
            "trial_time": "User.TrialTime",
            "file_date": "User.FileDate",
            "bop_due_date": "User.BOPDueDate",
            "date": "User.Date3",
            "day": "User.Day",
            "month": "User.Month",
            "year": "User.Year",
        },
        "defense_map": {
            # Map defense keys to checkboxes
            "CB1": "CB1",  # Generic checkbox — needs state-specific logic
        },
        "defense_options": [
            {"key": "def_not_owed", "label": "I do not owe the amount claimed"},
            {"key": "def_landlord_breach", "label": "The landlord breached the rental agreement"},
            {"key": "def_repairs", "label": "Landlord failed to maintain premises"},
            {"key": "def_retaliation", "label": "The eviction is in retaliation"},
            {"key": "def_discrimination", "label": "The eviction is discriminatory"},
            {"key": "def_bad_notice", "label": "I did not receive proper notice"},
        ],
        "notes": "DC-442 Grounds of Defense — 26 fillable fields. Used in General District Court for unlawful detainer cases.",
    },

    # ══════════════════════════════════════════
    # SOUTH CAROLINA — SCCA703 Answer
    # 22 fillable fields (descriptive names)
    # ══════════════════════════════════════════
    "SC": {
        "name": "South Carolina",
        "answer_form": "sc_eviction_answer.pdf",
        "fee_waiver_form": "sc_fee_waiver.pdf",
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
    # 55 fillable fields
    # ══════════════════════════════════════════
    "TX": {
        "name": "Texas",
        "answer_form": "tx_eviction_answer.pdf",
        "fee_waiver_form": "tx_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Justice of the Peace Court",
        "field_mapping": {
            "case_number": "Text1",
            "full_name": "Text5",
            "phone": "Text8",
            "date": "Text9",
            "email": "Text277",
        },
        "checkbox_mapping": {
            "jp_court": "Check Box JP",
            "county_court": "Check CountyCourt",
            "does_not_live": "Check Box Does Not Live",
            "mitigate_damages": "Check Box Mitigate",
            "fair_housing": "Check BoxFHAM",
            "counterclaim": "Check BoxCD",
            "other_court": "Other Court",
        },
        "notes": "TX JP Court eviction answer. Generic Text fields. Sequential mapping: Text1=defendant, Text2=plaintiff, Text3=case#.",
    },

    # ══════════════════════════════════════════
    # ILLINOIS — Statewide eviction answer
    # 156 fillable fields (complex, multi-page)
    # ══════════════════════════════════════════
    "IL": {
        "name": "Illinois",
        "answer_form": "il_eviction_answer.pdf",
        "fee_waiver_form": "il_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Circuit Court",
        "field_mapping": {
            "county": "1 - County",
            "full_name": "5 - Defendants (First, middle, last name)",
            "landlord_name": "2 - Plaintiff Name (First, Middle, Last)",
            "case_number": "9 - Case Number",
            "property_address": "10 - Property Address",
        },
        "notes": "IL Circuit Court eviction answer. 189 field widgets across 6 pages with admit/deny paragraph structure.",
    },

    # ══════════════════════════════════════════
    # CONNECTICUT — JD-HM-5 Summary Process Answer
    # 66 fillable fields
    # ══════════════════════════════════════════
    "CT": {
        "name": "Connecticut",
        "answer_form": "ct_eviction_answer.pdf",
        "fee_waiver_form": "ct_fee_waiver.pdf",
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
            "front": "FRONT[0]",
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
        "notes": "CT JD-HM-5 form. 66 fields with array indexing [0]. Used in Summary Process (eviction) cases.",
    },

    # ══════════════════════════════════════════
    # NORTH CAROLINA — AOC-CVM-201 Complaint in Summary Ejectment
    # 65 fillable fields
    # ══════════════════════════════════════════
    "NC": {
        "name": "North Carolina",
        "answer_form": "nc_eviction_answer.pdf",
        "fee_waiver_form": "nc_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "District Court / Magistrate",
        "field_mapping": {
            "full_name": "Defendant1Name",
            "landlord_name": "PlaintiffName",
            "case_number": "FileNumber",
            "property_address": "PremisesDescription",
            "county": "CountyName",
        },
        "notes": "NC AOC-CVM-201 is the complaint form (landlord filing). Tenant fills Defendant sections. 65 fields.",
    },

    # ══════════════════════════════════════════
    # RHODE ISLAND — District Court Eviction Answer
    # 51 fillable fields
    # ══════════════════════════════════════════
    "RI": {
        "name": "Rhode Island",
        "answer_form": "ri_eviction_answer.pdf",
        "fee_waiver_form": "ri_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "District Court",
        "field_mapping": {
            "full_name": "Defendant",
            "landlord_name": "Plaintiff",
            "case_number": "Civil Action File Number",
            "phone": "Telephone Number",
            "date": "Date",
        },
    },

    # ══════════════════════════════════════════
    # COLORADO — JDF 103 Eviction Answer
    # 6 pages, 57 fillable fields
    # ══════════════════════════════════════════
    "CO": {
        "name": "Colorado",
        "answer_form": "co_eviction_answer.pdf",
        "fee_waiver_form": "co_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "County Court",
        "field_mapping": {
            "address": "5",
            "case_number": "2",
            "county": "3",
            "full_name": "0",
            "landlord_name": "1",
            "phone": "4",
        },
        "notes": "JDF 103 Eviction Answer. 6 pages. Field names are numbered 0-56.",
    },

    # ══════════════════════════════════════════
    # LOUISIANA — Eviction Answer (LSBA form)
    # 14 pages, 62 fillable fields (checkbox based)
    # ══════════════════════════════════════════
    "LA": {
        "name": "Louisiana",
        "answer_form": "la_eviction_answer.pdf",
        "fee_waiver_form": "la_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "District Court / City Court",
        "field_mapping": {
            "defendant_name": "",
            "plaintiff_name": "",
        },
        "defense_options": [
            {"key": "def_not_violate_lease", "label": "I did not commit the lease violations", "field": "I did not commit the lease violations stated by my landlord"},
            {"key": "def_no_notice", "label": "I did not receive notice to vacate", "field": "I did not receive a Notice to Vacate I have a tenantbased Section 8 voucher so"},
            {"key": "def_section8", "label": "Section 8 / government housing protections", "field": "I do not owe the rent because I am on Section 8 or another government housing"},
            {"key": "def_ownership", "label": "I have ownership interest in the property", "field": "I have an ownership interest in the property I am being evicted from"},
            {"key": "def_general", "label": "I have exceptions or defenses", "field": "I have exceptions andor defenses to the claims made in the eviction paperwork"},
        ],
        "notes": "LA LSBA eviction answer form. Has good checkbox-style defense fields with descriptive names.",
    },

    # ══════════════════════════════════════════
    # MISSISSIPPI — Justice Court Answer
    # 2 pages, 9 fillable fields
    # ══════════════════════════════════════════
    "MS": {
        "name": "Mississippi",
        "answer_form": "ms_eviction_answer.pdf",
        "fee_waiver_form": "ms_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Justice Court",
        "field_mapping": {
            "full_name": "undefined",
            "landlord_name": "undefined",
            "county": "COUNTY MISSISSIPPI",
            "court_name": "IN THE JUSTICE COURT OF",
        },
        "notes": "MS Justice Court eviction answer. MS has undefined field names — needs form replacement.",
    },

    # ══════════════════════════════════════════
    # TENNESSEE — Sworn Denial (General Sessions)
    # 2 pages, 20 fillable fields
    # ══════════════════════════════════════════
    "TN": {
        "name": "Tennessee",
        "answer_form": "tn_eviction_answer.pdf",
        "fee_waiver_form": "tn_fee_waiver.pdf",
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
            "certification_2": "cert_2",
        },
        "notes": "TN Sworn Denial form. Has clean field names (court, county, file_number, etc.).",
    },

    # ══════════════════════════════════════════
    # CALIFORNIA — UD-105 Answer Unlawful Detainer
    # 4 pages, 154 fillable fields
    # ══════════════════════════════════════════
    "CA": {
        "name": "California",
        "answer_form": "ca_ud105.pdf",
        "fee_waiver_form": "ca_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Superior Court",
        "field_mapping": {
            "case_number": "UD-105[0].Page1[0].P1Caption[0].CaptionSub[0].CaseNumber[0].CaseNumber[0]",
            "attorney_bar_no": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].AttyBarNo[0]",
            "attorney_name": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Name[0]",
            "attorney_firm": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].AttyFirm[0]",
            "address": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Street[0]",
            "city": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].City[0]",
            "state": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].State[0]",
            "zip": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Zip[0]",
            "phone": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Phone[0]",
            "email": "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].Email[0]",
            "county": "UD-105[0].Page1[0].P1Caption[0].CourtInfo[0].CrtCounty[0]",
        },
        "notes": "CA UD-105 form. Field names use XFA dotted path notation (e.g., UD-105[0].Page1[0]...).",
    },

    # ══════════════════════════════════════════
    # ARKANSAS — Unlawful Detainer Answer Packet
    # 11 pages (scanned, overlay needed)
    # ══════════════════════════════════════════
    "AR": {
        "name": "Arkansas",
        "answer_form": "ar_eviction_answer.pdf",
        "fee_waiver_form": "ar_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "District Court",
        "overlay_positions": {
            "full_name": {"page": 9, "x": 90, "y": 620, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 7, "x": 200, "y": 70, "w": 200, "h": 20, "size": 11},
            "landlord_name": {"page": 9, "x": 90, "y": 650, "w": 300, "h": 20, "size": 11},
            "address": {"page": 10, "x": 110, "y": 81, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 10, "x": 360, "y": 134, "w": 150, "h": 20, "size": 11},
        },
        "notes": "AR unlawful detainer answer packet from Arkansas Justice. 11 pages including instructions.",
    },

    # ══════════════════════════════════════════
    # ARIZONA — Answer (LJEA00004F) + MHJCEA2I Instructions
    # Answer form is 2 pages, scanned
    # ══════════════════════════════════════════
    "AZ": {
        "name": "Arizona",
        "answer_form": "az_answer_form.pdf",
        "instructions_form": "az_eviction_answer.pdf",
        "fee_waiver_form": "az_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Justice Court / Superior Court",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 400, "w": 300, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 72, "y": 420, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 2, "x": 130, "y": 37, "w": 200, "h": 20, "size": 11},
        },
        "notes": "AZ answer form is scanned (no fillable fields). LJEA00004F is the official form. MHJCEA2I contains instructions.",
    },

    # ══════════════════════════════════════════
    # FLORIDA — Form 1.947(b) Answer Residential Eviction (generated)
    # Standardized form generated by the packet system
    # ══════════════════════════════════════════
    "FL": {
        "name": "Florida",
        "answer_form": "answer_form_917.pdf",
        "fee_waiver_form": "fl_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "County Court",
        "notes": "FL uses generated documents from the packet system rather than fillable PDFs. Fee waiver is scanned (fl_fee_waiver.pdf).",
    },

    # ══════════════════════════════════════════
    # MINNESOTA — Housing Court Eviction Answer (HOU202)
    # 4 pages, has text labels
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
        },
        "notes": "MN Housing Court eviction answer form (HOU202). Has text labels that can be used for positioning.",
    },

    # ══════════════════════════════════════════
    # NEVADA — Summary Eviction Answer
    # Scanned form — overlay needed
    # ══════════════════════════════════════════
    "NV": {
        "name": "Nevada",
        "answer_form": "nv_answer_nonpayment.pdf",
        "fee_waiver_form": "nv_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Justice Court",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 100, "y": 200, "w": 300, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 100, "y": 300, "w": 300, "h": 20, "size": 11},
        },
        "notes": "NV summary eviction answer form (nonpayment). Large file (3.6 MB), scanned.",
    },

    # ══════════════════════════════════════════
    # OREGON — Eviction Answer
    # Fillable form
    # ══════════════════════════════════════════
    "OR": {
        "name": "Oregon",
        "answer_form": "or_eviction_answer.pdf",
        "fee_waiver_form": "or_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Circuit Court",
        "notes": "OR form is scanned/no fillable fields. Needs overlay or replacement.",
    },

    # ══════════════════════════════════════════
    # MICHIGAN — Summary Eviction Answer
    # Fillable form
    # ══════════════════════════════════════════
    "MI": {
        "name": "Michigan",
        "answer_form": "mi_eviction_answer.pdf",
        "fee_waiver_form": "mi_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "District Court",
        "notes": "MI form on disk is the landlord's 7-day notice (DC 241), not the tenant answer form. Needs correct answer form.",
    },

    # ══════════════════════════════════════════
    # NEW MEXICO — 4-907 Answer to Petition for Restitution
    # 1 page, has text labels
    # ══════════════════════════════════════════
    "NM": {
        "name": "New Mexico",
        "answer_form": "nm_eviction_answer.pdf",
        "fee_waiver_form": "nm_fee_waiver.pdf",
        "has_fillable_fields": False,
        "court_type": "Metropolitan Court",
        "overlay_positions": {
            "full_name": {"page": 1, "x": 100, "y": 200, "w": 300, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 100, "y": 400, "w": 300, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 200, "y": 80, "w": 200, "h": 20, "size": 11},
        },
        "notes": "NM 4-907 Answer to Petition for Restitution. Metro Court form for eviction defense.",
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
