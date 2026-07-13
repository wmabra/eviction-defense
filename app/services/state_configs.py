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
    # 57 fillable fields across 3 pages (generic Text# field names)
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
            "address": "Text18",
            "printed_name": "Text16",
            "signature_date": "D signature date",
        },
        "checkbox_mapping": {
            "jp_court": "Check Box JP",
            "county_court": "Check CountyCourt",
            "does_not_live": "Check Box50",
            "mitigate_damages": "Check Box Mitigate",
            "fair_housing": "Check BoxFHAM",
            "counterclaim": "Check BoxCD",
            "other_court": "Other Court",
        },
        "notes": "TX JP Court eviction answer. Generic Text#/Check Box# field names — requires explicit mapping since auto-fill can't interpret numbered fields. 57 fillable fields across 3 pages.",
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
    # 1 page, 62 fillable fields (defense/specialized fields only)
    # No defendant name field — uses overlay for tenant data
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
            "address": {"page": 1, "x": 72, "y": 220, "w": 300, "h": 20, "size": 10},
            "phone": {"page": 1, "x": 72, "y": 240, "w": 200, "h": 20, "size": 10},
        },
        "notes": "CT JD-HM-5 form — 62 fillable fields but NO defendant name/address field (form assumes case caption provides it). Tenant data (name, address, phone) uses overlay positions. Landlord info, docket number, and defenses use fillable fields.",
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
    # 4 pages, 51 fillable fields
    # ══════════════════════════════════════════
    "RI": {
        "name": "Rhode Island",
        "answer_form": "ri_eviction_answer.pdf",
        "fee_waiver_form": "ri_fee_waiver.pdf",
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
        "notes": "CO JDF 103 — 6 pages, 57 fillable fields. Page 1 has 14 named fields (∆=defendant, π=plaintiff). Pages 2-6 are defense checkboxes and signature fields.",
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
    # MISSISSIPPI — Justice Court Answer
    # 2 pages, broken fillable fields ("undefined" names)
    # Uses overlay positions for critical fields + auto-fill for the 2 named fields
    # ══════════════════════════════════════════
    "MS": {
        "name": "Mississippi",
        "answer_form": "ms_eviction_answer.pdf",
        "fee_waiver_form": "ms_fee_waiver.pdf",
        "has_fillable_fields": True,
        "court_type": "Justice Court",
        "field_mapping": {
            "county": "COUNTY MISSISSIPPI",
            "court_name": "IN THE JUSTICE COURT OF",
        },
        "overlay_positions": {
            "full_name": {"page": 1, "x": 72, "y": 630, "w": 250, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 72, "y": 670, "w": 250, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 400, "y": 90, "w": 200, "h": 20, "size": 11},
            "address": {"page": 1, "x": 72, "y": 700, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 1, "x": 72, "y": 720, "w": 200, "h": 20, "size": 11},
        },
        "notes": "MS Justice Court eviction answer. Most fillable fields have 'undefined' names — county and court are the only named widgets. Remaining tenant/landlord info uses overlay positions. Form needs a proper replacement (unknown if MS has an official fillable eviction answer form).",
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
        "static_values": {
            "UD-105[0].Page1[0].P1Caption[0].AttyPartyInfo[0].AttyFirm[0]": "In Pro Per",
        },
        "notes": "CA UD-105 — 154 fields, complex XFA dotted paths. Maps defendant (pro se) into AttyPartyInfo section — 'In Pro Per' goes in AttyFirm, defendant's name goes in AttyName, defendant's address in AttyStreet. Tenant self-represents.",
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
            "case_number": {"page": 7, "x": 300, "y": 45, "w": 200, "h": 20, "size": 11},
            "landlord_name": {"page": 9, "x": 90, "y": 650, "w": 300, "h": 20, "size": 11},
            "address": {"page": 10, "x": 110, "y": 81, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 10, "x": 360, "y": 134, "w": 150, "h": 20, "size": 11},
        },
        "notes": "AR unlawful detainer answer packet from Arkansas Justice. 11 pages including instructions.",
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
        },
        "notes": "AZ answer form (LJEA00004F) — scanned PDF, no fillable fields. Overlay positions cover all essential tenant/landlord/case fields. MHJCEA2I is the instructions companion PDF.",
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
        "overlay_positions": {
            "county": {"page": 1, "x": 54, "y": 72, "w": 250, "h": 20, "size": 10},
            "case_number": {"page": 1, "x": 380, "y": 95, "w": 170, "h": 20, "size": 10},
            "landlord_name": {"page": 1, "x": 54, "y": 175, "w": 300, "h": 22, "size": 11},
            "full_name": {"page": 1, "x": 54, "y": 230, "w": 300, "h": 22, "size": 11},
            "address": {"page": 1, "x": 54, "y": 260, "w": 350, "h": 20, "size": 10},
            "phone": {"page": 2, "x": 54, "y": 700, "w": 200, "h": 20, "size": 10},
            "email": {"page": 2, "x": 54, "y": 720, "w": 250, "h": 20, "size": 10},
        },
        "notes": "FL Form 1.947(b) Answer — Residential Eviction. Scanned form with overlay positions at estimated caption locations. The generator.py also creates a cleanly formatted version from scratch (superior output), but overlay fills the actual scanned official form.",
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
            "full_name": {"page": 1, "x": 200, "y": 277, "w": 200, "h": 20, "size": 11},
            "landlord_name": {"page": 1, "x": 200, "y": 188, "w": 200, "h": 20, "size": 11},
            "county": {"page": 1, "x": 75, "y": 106, "w": 200, "h": 20, "size": 11},
            "case_number": {"page": 1, "x": 420, "y": 126, "w": 150, "h": 20, "size": 11},
            "address": {"page": 1, "x": 72, "y": 327, "w": 300, "h": 20, "size": 11},
            "phone": {"page": 1, "x": 72, "y": 347, "w": 200, "h": 20, "size": 10},
            "date": {"page": 1, "x": 400, "y": 347, "w": 150, "h": 20, "size": 10},
        },
        "notes": "MN HOU202 Housing Court Eviction Answer — scanned PDF. Overlay positions for caption area fields + phone/date.",
    },

    # ══════════════════════════════════════════
    # NEVADA — Summary Eviction Answer (Nonpayment)
    # 65 fillable fields across 4 pages
    # ══════════════════════════════════════════
    "NV": {
        "name": "Nevada",
        "answer_form": "nv_answer_nonpayment.pdf",
        "fee_waiver_form": "nv_fee_waiver.pdf",
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
        },
        "notes": "OR FED Answer — scanned PDF. Overlay positions for essential fields on page 1 caption area.",
    },

    # ══════════════════════════════════════════
    # MICHIGAN — DC 111a Answer, Nonpayment of Rent
    # 48 fillable fields across 2 pages (replaced landlord notice form)
    # ══════════════════════════════════════════
    "MI": {
        "name": "Michigan",
        "answer_form": "mi_eviction_answer.pdf",
        "fee_waiver_form": "mi_fee_waiver.pdf",
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
        },
        "notes": "NM 4-907 Answer to Petition for Restitution — single-page scanned form. Overlay positions cover all essential fields.",
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
