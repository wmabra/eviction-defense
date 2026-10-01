"""AI-powered conversational intake — collects all data across 6 sections for 20 states."""
import json
import re
from typing import Optional
from openai import OpenAI
from app.config import settings
from app.services.state_configs import get_state_config

_client = None
_sessions: dict[str, dict] = {}  # case_id -> {phase, collected_data}


def _get_client():
    global _client
    if _client is None:
        api_key = settings.llm_api_key or settings.deepseek_api_key
        base_url = settings.llm_base_url or "https://api.deepseek.com/v1"
        model = settings.llm_model or "deepseek-chat"
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def get_model() -> str:
    return settings.llm_model or "deepseek-chat"


SUPPORTED_STATES = [
    "ALABAMA","ALASKA","ARIZONA","ARKANSAS","CALIFORNIA","COLORADO","CONNECTICUT",
    "DELAWARE","GEORGIA","HAWAII","IDAHO","ILLINOIS","INDIANA","IOWA",
    "KANSAS","KENTUCKY","LOUISIANA","MAINE","MARYLAND","MASSACHUSETTS","MICHIGAN",
    "MINNESOTA","MISSISSIPPI","MISSOURI","MONTANA","NEBRASKA","NEVADA","NEW HAMPSHIRE",
    "NEW JERSEY","NEW MEXICO","NEW YORK","NORTH CAROLINA","NORTH DAKOTA","OHIO",
    "OKLAHOMA","OREGON","PENNSYLVANIA","RHODE ISLAND","SOUTH CAROLINA","SOUTH DAKOTA",
    "TENNESSEE","TEXAS","UTAH","VERMONT","VIRGINIA","WASHINGTON","WEST VIRGINIA",
    "WISCONSIN","WYOMING"
]

# We ONLY serve these 20 states — the user already passed state eligibility before arriving
SERVED_STATES = {
    "AR","CO","CT","GA","IL","IN","KY","LA",
    "MI","MN","MO","NM","OH","OK","OR","RI","SC","TN","TX","VA"
}

STATE_NAMES = {
    "AR": "Arkansas", "CO": "Colorado", "CT": "Connecticut", "GA": "Georgia",
    "IL": "Illinois", "IN": "Indiana", "KY": "Kentucky", "LA": "Louisiana",
    "MI": "Michigan", "MN": "Minnesota", "MO": "Missouri", "NM": "New Mexico",
    "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon", "RI": "Rhode Island",
    "SC": "South Carolina", "TN": "Tennessee", "TX": "Texas", "VA": "Virginia"
}

STATE_NAME_TO_CODE = {
    "ALABAMA": "AL", "ALASKA": "AK", "ARIZONA": "AZ", "ARKANSAS": "AR",
    "CALIFORNIA": "CA", "COLORADO": "CO", "CONNECTICUT": "CT", "DELAWARE": "DE",
    "FLORIDA": "FL", "GEORGIA": "GA", "HAWAII": "HI", "IDAHO": "ID",
    "ILLINOIS": "IL", "INDIANA": "IN", "IOWA": "IA", "KANSAS": "KS",
    "KENTUCKY": "KY", "LOUISIANA": "LA", "MAINE": "ME", "MARYLAND": "MD",
    "MASSACHUSETTS": "MA", "MICHIGAN": "MI", "MINNESOTA": "MN", "MISSISSIPPI": "MS",
    "MISSOURI": "MO", "MONTANA": "MT", "NEBRASKA": "NE", "NEVADA": "NV",
    "NEW HAMPSHIRE": "NH", "NEW JERSEY": "NJ", "NEW MEXICO": "NM", "NEW YORK": "NY",
    "NORTH CAROLINA": "NC", "NORTH DAKOTA": "ND", "OHIO": "OH", "OKLAHOMA": "OK",
    "OREGON": "OR", "PENNSYLVANIA": "PA", "RHODE ISLAND": "RI", "SOUTH CAROLINA": "SC",
    "SOUTH DAKOTA": "SD", "TENNESSEE": "TN", "TEXAS": "TX", "UTAH": "UT",
    "VERMONT": "VT", "VIRGINIA": "VA", "WASHINGTON": "WA", "WEST VIRGINIA": "WV",
    "WISCONSIN": "WI", "WYOMING": "WY"
}

STATE_PROFILES = {
    "AR": {
        "court_type": "District Court / Circuit Court",
        "repair_question": "h. Did you send a written 14-day repair notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, SSI, Medicaid, or TANF)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Arkansas eviction cases are heard in District Court (or Circuit Court for ejectment).",
            "- Ark. Code § 18-17-701 provides tenant remedies following a written 14-day repair notice.",
            "- In Forma Pauperis (Fee Waiver) requires monthly income, expense breakdown, and public assistance programs.",
        ],
    },
    "CO": {
        "court_type": "County Court",
        "repair_question": "h. Did you send a written notice of uninhabitable condition to the landlord? (yes/no)",
        "has_jury_demand": True,
        "cos_type": "colorado",
        "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, Medicaid, SSI, TANF, Aid to the Blind, Aid to the Needy and Disabled (AND), Old Age Pension (OAP), Section 8, or energy assistance)?",
        "household_question_type": "table",
        "ask_bank_name": True,
        "has_county_rule": "denver",
        "profile_notes": [
            "- Colorado County Court uses statewide Answer Form (JDF 103) or Denver County Court uses DCC CP No. 3.",
            "- Colorado statewide Answer Form (JDF 103): Defenses are grouped into Section 7a (Unpaid Rent claims), Section 7b (Lease Violation claims), Section 7c (Substantial Violation claims), Section 7d (Ending Tenancy/No-Fault non-renewal), and Section 7e (General Defenses). Ensure Section 7e (unallowed fees under lease, illegal late fees under C.R.S. 38-12-105, improper notice/cure period, Unfair Housing Act discrimination, failure to attend mandatory mediation) is clearly offered to the tenant so general defenses are not overlooked or left blank.",
            "- Colorado Certificate of Service (#10): Always ask how the tenant will deliver/serve the answer to the landlord or their attorney (regular mail, Colorado Courts E-Filing, or hand delivery/other).",
            "- Colorado Fee Waiver (JDF 205): Automatic Qualification applies to SNAP, SSI, TANF, Aid to the Blind Colorado, Aid to the Needy and Disabled (AND), and Old Age Pension (OAP). Include these programs in your public assistance questions.",
            "- Colorado Fee Waiver Sections 8 & 10: Ask for the names, ages, and relationships of household members (Section 8) and the name of the tenant's bank or credit union (Section 10).",
        ],
    },
    "CT": {
        "court_type": "Housing Court / Superior Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, TFA / Temporary Family Assistance, SAGA, Medicaid, or SSI)?",
        "household_question_type": "dependents_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Connecticut Housing Session / Superior Court uses Form JD-HM-5 (Summary Process Answer).",
            "- Form JD-HM-5 contains a standard service certification to the plaintiff or attorney; do not prompt the user for delivery method.",
            "- Connecticut Fee Waiver (Form JD-CV-120) asks for total number of dependents, monthly income/expense schedule, and categorical programs (SNAP, TFA, SAGA, Medicaid, SSI).",
        ],
    },
    "GA": {
        "court_type": "Magistrate Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as TANF, SNAP/food stamps, Medicaid, or SSI)?",
        "household_question_type": "table",
        "ask_bank_name": True,
        "profile_notes": [
            "- Georgia Magistrate Court uses the statewide Dispossessory Answer form across all 159 Georgia counties.",
            "- Georgia Pauper's Affidavit fee waiver asks for household dependents table, employer, bank name, liabilities, and hardship circumstances.",
        ],
    },
    "IL": {
        "court_type": "Circuit Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": True,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, SSI, TANF, AABD, General Assistance, Medicaid, Section 8, or energy assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "has_county_rule": "cook",
        "profile_notes": [
            "- Illinois Circuit Court uses the statewide Appearance and Eviction Answer form (includes jury demand option).",
            "- Cook County has municipal district divisions but accepts statewide forms.",
            "- Fee Waiver: Automatic / categorical qualification applies to SNAP, SSI, TANF, AABD, General Assistance, and Medicaid.",
        ],
    },
    "IN": {
        "court_type": "Superior Court / Circuit Court / Small Claims",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, TANF, SSI, Medicaid, or energy assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Indiana eviction cases are filed in Superior, Circuit, or Small Claims Courts.",
            "- Statewide Answer and Fee Waiver forms.",
        ],
    },
    "KY": {
        "court_type": "District Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, KTAP, SSI, Medicaid, or Section 8)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Kentucky District Court handles Forcible Detainer actions.",
            "- Statewide Forcible Detainer Answer and Motion to Proceed In Forma Pauperis.",
        ],
    },
    "LA": {
        "court_type": "City Court / Parish Court / Justice of the Peace",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, FITAP, SSI, Medicaid, or housing assistance)?",
        "household_question_type": "table",
        "ask_bank_name": True,
        "profile_notes": [
            "- Louisiana City Court / Parish Court eviction procedure.",
            "- IFP application includes household member table and financial institution name.",
        ],
    },
    "MI": {
        "court_type": "District Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": True,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, FIP, SSI, Medicaid, or state emergency relief)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Michigan District Court uses Form DC 111a (Answer, Nonpayment of Rent), which includes a jury demand checkbox.",
            "- Fee Waiver Form MC 20 (Waiver/Suspension of Fees).",
        ],
    },
    "MN": {
        "court_type": "District Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, MFIP, GA, SSI, MA/Medicaid, or energy assistance)?",
        "household_question_type": "table",
        "ask_bank_name": False,
        "profile_notes": [
            "- Minnesota District Court (Housing Court in Hennepin and Ramsey counties) uses Form HOU202.",
            "- Fee Waiver IFP form includes household members schedule.",
        ],
    },
    "MO": {
        "court_type": "Associate Circuit Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, TANF, SSI, Medicaid, or utility assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Missouri Associate Circuit Court eviction defense.",
            "- Answer and In Forma Pauperis Fee Waiver Affidavit.",
        ],
    },
    "NM": {
        "court_type": "Magistrate Court / Metropolitan Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, TANF, SSI, Medicaid, or GA)?",
        "household_question_type": "counts_only",
        "ask_bank_name": True,
        "profile_notes": [
            "- New Mexico Magistrate Court / Bernalillo County Metropolitan Court uses Form 4-907.",
            "- Free Process application asks for bank name and public assistance.",
        ],
    },
    "OH": {
        "court_type": "Municipal Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, OWF, SSI, Medicaid, or housing assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Ohio Municipal Court Forcible Entry and Detainer action.",
            "- Form 20 Civil Fee Waiver Affidavit.",
        ],
    },
    "OK": {
        "court_type": "District Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, TANF, SSI, Medicaid, or energy assistance)?",
        "household_question_type": "table",
        "ask_bank_name": False,
        "profile_notes": [
            "- Oklahoma District Court FED Answer.",
            "- Pauper's Affidavit fee waiver includes household members schedule.",
        ],
    },
    "OR": {
        "court_type": "Circuit Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": True,
        "cos_type": "options",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, TANF, SSI, OHP/Medicaid, or energy assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Oregon Circuit Court Residential Eviction (FED) Answer.",
            "- Form includes jury trial request and certificate of service delivery methods (mail, hand delivery, commercial delivery).",
            "- OJD Fee Deferral/Waiver Application.",
        ],
    },
    "RI": {
        "court_type": "District Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "options",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, RI Works, SSI, Medicaid, or GPA)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Rhode Island District Court Eviction Answer.",
            "- Includes defense checkboxes and service method options (mail, hand delivery, electronic).",
            "- In Forma Pauperis fee waiver.",
        ],
    },
    "SC": {
        "court_type": "Magistrates Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, Medicaid, TANF, SSI, Section 8, or energy assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- South Carolina Magistrates Court Form SCCA703.",
            "- Form SCCA703 mutual exclusivity: partial responsibility (with explanation) vs full denial.",
            "- Form SCCA405 fee waiver auto-maps county to judicial circuit.",
        ],
    },
    "TN": {
        "court_type": "General Sessions Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": True,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public assistance (such as SNAP/food stamps, Families First/TANF, SSI, TennCare/Medicaid, or housing assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Tennessee General Sessions Court Form Sworn Denial (includes jury demand option).",
            "- Uniform Indigency Affidavit fee waiver overlay.",
        ],
    },
    "TX": {
        "court_type": "Justice of the Peace Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": True,
        "cos_type": "options",
        "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, Medicaid, SSI, TANF, WIC, Section 8, or energy assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Texas Justice Court Eviction Answer (defense checkboxes, Box 54 amount dispute, jury demand, service method).",
            "- Statement of Inability to Afford Payment of Court Costs (categorical qualification for SNAP, TANF, Medicaid, SSI, WIC).",
        ],
    },
    "VA": {
        "court_type": "General District Court",
        "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
        "has_jury_demand": False,
        "cos_type": "standard",
        "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, TANF, Medicaid, SSI, Section 8, or energy assistance)?",
        "household_question_type": "counts_only",
        "ask_bank_name": False,
        "profile_notes": [
            "- Virginia General District Court Form DC-442 (Grounds of Defense with numbered defense text fields User.1-User.5, Defendant role).",
            "- Form CC-1414 Fee Waiver (categorical assistance: TANF, Medicaid, SSI, SNAP).",
        ],
    },
}

DEFAULT_PROFILE = {
    "court_type": "",
    "repair_question": "h. Did you send a written repair request or notice to the landlord? (yes/no)",
    "has_jury_demand": False,
    "cos_type": "standard",
    "benefits_question": "Do you receive any public benefits (such as SNAP/food stamps, Medicaid, SSI, TANF, Section 8, or energy assistance)?",
    "household_question_type": "counts_only",
    "ask_bank_name": False,
    "profile_notes": [],
}

GENERIC_DEFENSE_LIST = """1. def_repairs — The landlord did not make repairs after written notice
2. def_amount — I do not owe the total amount of rent claimed
3. def_attempted_pay — I attempted or offered to pay, but the landlord refused
4. def_paid — I already paid the rent demanded
5. def_waived — The landlord waived, changed, or canceled the notice
6. def_retaliation — The eviction is retaliatory
7. def_fair_housing — The eviction violates fair housing law
8. def_accepted_rent — The landlord accepted rent after sending the notice
9. def_corrected — I already corrected the violation the landlord claimed
10. def_not_owner — The person suing me is not the owner
11. def_bad_notice — I did not receive proper legal notice
12. def_other — Other defenses"""

NARRATIVE_DEFENSE_INSTRUCTION = """(NARRATIVE ANSWER FORM — no fixed checkbox list.) Your answer form asks the tenant to state their defenses in their own words. Ask: "What is your side of the story? What reasons do you want to give the court for why you should not be evicted?" Type their answer word for word. Do NOT suggest defenses or explain any legal concept. If they mention specific defenses (for example, repairs not made, rent already paid, improper notice), ask for brief facts to support each one. In the final JSON, store their statement under defenses: {"narrative": {"checked": true, "explanation": "<user's statement word for word>"}}."""


def _defense_list_for_state(state: Optional[str], county: Optional[str]) -> str:
    """Return the answer-form defense list for a state (or a narrative
    instruction when the state's form has no discrete checkboxes)."""
    state = (state or "").upper()
    state = STATE_NAME_TO_CODE.get(state, state)
    county = (county or "").strip()

    # Denver County Court uses its own narrative answer form, not the
    # statewide JDF 103 checkbox form.
    if state == "CO" and county.lower() == "denver":
        return NARRATIVE_DEFENSE_INSTRUCTION

    cfg = get_state_config(state)
    if cfg:
        options = cfg.get("defense_options") or []
        if options:
            lines: list[str] = []
            seen: set[str] = set()
            curr_section = None
            item_num = 1
            for opt in options:
                sec = opt.get("section")
                if sec and sec != curr_section:
                    curr_section = sec
                    if lines:
                        lines.append("")
                    lines.append(f"[{sec}]")
                key = opt.get("key", "")
                if not key or key in seen:
                    continue
                seen.add(key)
                label = opt.get("label") or key
                lines.append(f"{item_num}. {key} — {label}")
                item_num += 1
            return "\n".join(lines)

    # AR, MN, and any other narrative/scanned form fall back to the generic list.
    return GENERIC_DEFENSE_LIST


def _state_profile(state: Optional[str], county: Optional[str]) -> str:
    """A short, human-relevant profile so the specialist asks the right court
    and form questions for this state."""
    state = (state or "").upper()
    state = STATE_NAME_TO_CODE.get(state, state)
    county = (county or "").strip()
    profile = STATE_PROFILES.get(state, DEFAULT_PROFILE)
    lines: list[str] = []

    court_type = profile.get("court_type")
    if court_type:
        lines.append(f"- Court type: {court_type}")

    notes = profile.get("profile_notes", [])
    if state == "CO":
        if county.lower() == "denver":
            lines.append("- Denver County Court uses its own answer form (DCC CP No. 3), not the statewide JDF 103 form.")
            lines.append("- Colorado Certificate of Service: Ask how the tenant will deliver/serve the answer to the landlord or their attorney (regular mail, Colorado Courts E-Filing, or hand delivery/other).")
            lines.append("- Colorado Fee Waiver (JDF 205): Automatic Qualification applies to SNAP, SSI, TANF, Aid to the Blind Colorado, AND, OAP. Sections 8 & 10 require household members and bank name.")
        else:
            lines.extend(notes)
    else:
        lines.extend(notes)

    return "\n".join(lines)


def _build_intro(state: Optional[str]) -> str:
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)
    if st in SERVED_STATES:
        name = STATE_NAMES.get(st, st)
        return (
            f"You are an intake specialist for evictions.help, an AI-powered self-help document preparation service. "
            f"You are currently assisting a tenant with an active eviction case in the State of {name} ({st}).\n\n"
            f"IMPORTANT: The user has already passed eligibility screening AND paid for this service for {name}. "
            f"NEVER tell the user that you don't serve their state. Conversationally collect ONLY the information needed "
            f"for {name} court forms, legal motions, checklists, hearing scripts, rental assistance, and fee waiver forms. "
            f"Be warm, supportive, concise, and professional."
        )
    return (
        "You are an intake specialist for evictions.help, an AI-powered self-help document preparation service serving 20 states: "
        "AR, CO, CT, GA, IL, IN, KY, LA, MI, MN, MO, NM, OH, OK, OR, RI, SC, TN, TX, VA.\n\n"
        "IMPORTANT: The user has already passed eligibility screening AND paid for this service. "
        "They are from one of our 20 covered states. NEVER tell a user that you don't serve their state. "
        "Conversationally collect ALL information needed to prepare a complete eviction defense packet. "
        "Be warm, supportive, concise, and professional."
    )


def _build_phase1(state: Optional[str], county: Optional[str]) -> str:
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)
    lines = [
        "=== PHASE 1: PERSONAL & LOCATION INFO ===",
        "NOTE: The tenant has ALREADY confirmed they have been served with court papers and have an active case number during the initial eligibility screening before payment. Do NOT ask whether they have been served with court papers.",
        "",
        "FIRST TURN (OPENING NAME ANSWER):",
        'The chat opens with the welcome message asking: "what is your full legal name, exactly as it appears on your eviction notice or lease?".',
        "When the user replies to that opening message with their name (e.g. \"Mark Daniel Kreischer\"):",
        "- Acknowledge their name (e.g. \"Thanks, Mark.\").",
        "- Record it as their full legal name.",
        "- IMMEDIATELY advance to step b and ask for their date of birth (MM/DD/YYYY).",
        "- NEVER ask for their full legal name a second time! You already asked in the opening message and they just answered it.",
        "",
        "Collect these fields in order, ONE QUESTION PER MESSAGE:",
        "a. Full legal name (already asked in opening welcome message — do not repeat if provided)",
        "b. Date of birth (MM/DD/YYYY) — REQUIRED for fee waiver and court identification",
        "c. County (where the eviction case is filed) — DO NOT ask about state, the user already passed state eligibility",
    ]
    if st == "CO":
        lines.extend([
            "",
            "SPECIAL COUNTY RULE (Colorado only): Denver is its own city-and-county, distinct from the surrounding counties. If the case is filed in Denver County Court (the property and courthouse are inside the City and County of Denver), record county as exactly \"Denver\". If the user is in a Denver-area suburb or any other Colorado county (Jefferson, Arapahoe, Adams, Douglas, Boulder, Broomfield, El Paso, Larimer, etc.), record that ACTUAL county — never \"Denver\". When a Colorado user says \"Denver\" or \"the Denver area\", confirm whether the courthouse is \"Denver County Court\" (record \"Denver\") or a different county's court (record that county). Never guess or assume.",
        ])
    elif st == "IL":
        lines.extend([
            "",
            "SPECIAL COUNTY RULE (Illinois only): If the eviction is filed in Cook County, record county as exactly \"Cook\".",
        ])
    lines.extend([
        "",
        "d. Street address being evicted from (street number and name ONLY) — record as property_address (do NOT include city or zip here)",
        "e. City — record as property_city",
        "f. ZIP code (5 digits) — record as property_zip",
        "g. Cell phone number — REQUIRED (for your records)",
        "h. Email address (to receive completed packet) — REQUIRED",
        "i. Are you the tenant named in the eviction? (if no, explain we can only help the named tenant)",
        "j. Do you need a foreign language interpreter for court hearings? (Reply 'No', or 'Yes' with the language you need) — REQUIRED for court scheduling.",
    ])
    return "\n".join(lines)


def _build_phase2(state: Optional[str]) -> str:
    return """=== PHASE 2: LANDLORD & CASE INFO ===
STRICT NO-COMBO RULE: Every single question below MUST be asked in its own separate message. NEVER ask combined questions (e.g. NEVER ask for phone AND email together; NEVER ask if an attorney is listed AND their name/address in one question).

Collect these fields in order, ONE QUESTION PER MESSAGE:
a. Landlord or company name EXACTLY as on eviction notice/summons — REQUIRED (this is the plaintiff on the case)
b. Landlord's full mailing address (street, city, state, ZIP) — REQUIRED. Ask tenant to copy it exactly from the summons.
c. Is there a phone number listed for your landlord? (If not listed or you don't know, reply 'None') — ASK PHONE ONLY.
d. Is there an email address listed for your landlord? (If not listed or you don't know, reply 'None') — ASK EMAIL ONLY IN A SEPARATE MESSAGE.
e. Is an attorney listed on the court papers or summons for your landlord? (yes/no) — ASK ONLY YES/NO FIRST.
f. If yes: What is the landlord's attorney's name? — ASK NAME ONLY.
g. If yes: What is the landlord's attorney's full mailing address? (If unknown, reply 'None') — ASK ADDRESS IN A SEPARATE MESSAGE.
h. Case number (printed near the top of court papers/summons)
i. Court name (what is the name of the courthouse where the case was filed? You can also include the court address from your summons) — ASK ONLY THE COURTHOUSE NAME / ADDRESS HERE.
j. Court division (is there a division listed on your summons, such as Division 1 or Civil Division? If none or not shown, they can say None) — ASK IN A SEPARATE MESSAGE.
k. When were you served with the court papers? (date on summons)
l. Did you receive a notice to pay or quit before the court papers were served? (yes/no)
m. How much rent does the landlord claim you owe in the complaint? (dollar amount)
n. Do you have a court date scheduled? (yes/no) — ASK ONLY YES/NO FIRST.
o. If yes: What date is your court hearing?
p. If yes: What time is your court hearing? (e.g. 9:00 AM)
q. Do you know your response deadline? (check summons — usually 5-20 days)"""


def _build_phase3(state: Optional[str]) -> str:
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)
    profile = STATE_PROFILES.get(st, DEFAULT_PROFILE)
    repair_q = profile.get("repair_question", "h. Did you send a written repair request or notice to the landlord? (yes/no)")

    return f"""=== PHASE 3: RENT & PAYMENT DETAILS ===
Collect these fields in order, ONE QUESTION PER MESSAGE:
a. What is your monthly rent amount?
b. Do you agree with the amount of rent the landlord claims you owe? (yes/no)
c. If no: How much rent do you believe you actually owe?
d. If no: Why do you disagree with the amount claimed?
e. Have you paid any rent after receiving the eviction notice? (yes/no)
   - If yes: In your next message, ask: "Approximately what date did you pay or offer the rent?" (record under rent_paid_date in rent_payment).
f. Have you applied for rental assistance? (yes/no)
g. If yes: What is the current status of your rental assistance application?
{repair_q}
i. If yes to sending a repair notice: Approximately what date (or month/year) did you send the repair notice to your landlord? (record under repair_notice_date in rent_payment)"""


def _build_phase4(state: Optional[str], county: Optional[str]) -> str:
    defense_list = _defense_list_for_state(state, county)
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)
    is_narrative = (st == "CO" and (county or "").strip().lower() == "denver")

    if is_narrative:
        return f"""=== PHASE 4: DEFENSES ===
LEGAL SAFETY RULE (ABSOLUTE): You must NOT advise the tenant on which defenses to select, explain what any defense means, or suggest that a defense applies to their situation. Doing so is legal advice and is prohibited. You are only a typing assistant: the tenant chooses, and you type their choices.

{defense_list}"""

    return f"""=== PHASE 4: DEFENSES ===
LEGAL SAFETY RULE (ABSOLUTE): You must NOT advise the tenant on which defenses to select, explain what any defense means, or suggest that a defense applies to their situation. Doing so is legal advice and is prohibited. You are only a typing assistant: the tenant chooses, and you type their choices.

Acknowledge completion of the rent section and present the defenses clearly with separate paragraphs:
"Thank you — that completes the rent and payment section.

Now let's look at defenses. Your state's official answer form includes a checklist of legal defenses. I cannot advise you on which ones apply to your situation, but please review the list below and reply with the number(s) you want to check (for example: 1, 1 and 4, or 12), or reply 'None' if none apply:

{defense_list}

Which number(s) would you like to check?"

Read the checklist to the user EXACTLY as worded on the official form (do not paraphrase, do not add examples, do not explain). Each item below shows the internal key (before the "—") followed by the exact form wording — read only the wording to the user, and remember the key for the JSON you output later.

Accept the user's explicit selections. Do NOT ask whether a particular situation occurred (e.g., do not ask "did your landlord fix things?"). Do NOT explain any defense or add examples.

For EACH defense the user explicitly selects, ask: "The form asks for brief facts to support each defense you check. What would you like me to type for this one?" Type only what the user says, word for word.

If the user asks for help choosing, asks what a defense means, or asks whether one applies: "I'm not able to advise you on which defenses apply to your situation. Please select the ones you believe apply, or contact your local legal aid office for guidance.\""""


def _build_phase5(state: Optional[str]) -> str:
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)
    profile = STATE_PROFILES.get(st, DEFAULT_PROFILE)

    has_jury = profile.get("has_jury_demand", False)
    cos_type = profile.get("cos_type", "standard")

    raw_items: list[tuple[bool, str]] = []  # (is_user_facing, text)

    if has_jury:
        raw_items.append((True, "The official court form asks whether you want a judge trial or a jury trial. Which do you prefer?"))

    if cos_type == "colorado":
        raw_items.append((True, "How will you deliver a copy of your answer to the landlord or their attorney? (By regular mail, Colorado Courts E-Filing, or hand delivery/other — default is regular mail; record under certificate_of_service_method: regular_mail, efile, other)"))
    elif cos_type == "options":
        raw_items.append((True, "How will you deliver a copy of your answer to the landlord or their attorney? (By regular mail, electronic delivery, or hand delivery — default is regular mail; record under certificate_of_service_method: regular_mail, efile, other)"))
    else:
        name = STATE_NAMES.get(st, "this state")
        raw_items.append((False, f"(NOTE: The official {name} answer form uses standard service certification. Do not ask the user for a delivery method; default certificate_of_service_method to 'regular_mail' in the background.)"))

    raw_items.extend([
        (True, "Would you like a formal hardship letter to send to your landlord explaining your financial situation and asking for more time? (yes/no)"),
        (True, "If yes: What is the reason for hardship you would like stated in the letter to your landlord? (record as hardship_reason; if user answers no, set needs_more_time to false)"),
        (True, "Would you like to propose a formal payment plan letter to your landlord? (yes/no)"),
        (True, "If yes: What monthly payment amount would you like to propose? (IMPORTANT: If the user says no, or indicates they already tried and the landlord refused/rejected it, set wants_payment_plan to false.)"),
        (True, "Are you facing an immediate lockout by the sheriff? (yes/no)"),
        (True, "Would you like to file a Motion for Continuance with the court to postpone your scheduled hearing date? (yes/no)"),
        (True, "If yes: What is the reason you are asking the court for a postponement? (For example: to arrange funds or negotiate a payment plan, to find/consult an attorney, to gather evidence and documents, to deal with personal/family circumstances, or other reasons?)"),
        (True, "If yes: How many days would you like the court to postpone the hearing? (e.g., 14, 30 days — default is 30 days)"),
        (True, "Would you like to request an emergency stay from the court to pause the eviction? (yes/no)"),
        (True, "If yes: What is the emergency reason?"),
        (True, "If yes: How many days emergency stay are you requesting? (default is 30 days)"),
    ])

    formatted_lines: list[str] = []
    idx = 0
    for is_user_facing, text in raw_items:
        if is_user_facing:
            letter = chr(ord('a') + idx)
            formatted_lines.append(f"{letter}. {text}")
            idx += 1
        else:
            formatted_lines.append(text)

    questions_block = "\n".join(formatted_lines)
    return f"""=== PHASE 5: PREFERENCES & MOTIONS ===
Ask each question individually, ONE QUESTION PER MESSAGE:
{questions_block}"""


def _build_phase6(state: Optional[str]) -> str:
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)
    profile = STATE_PROFILES.get(st, DEFAULT_PROFILE)

    benefits_q = profile.get("benefits_question", "Do you receive any public benefits (such as SNAP/food stamps, Medicaid, SSI, TANF, Section 8, or energy assistance)?")
    hh_type = profile.get("household_question_type", "counts_only")
    ask_bank = profile.get("ask_bank_name", False)

    if hh_type == "dependents_only":
        hh_block = """g. How many dependents do you support? (Do not count yourself; record under total_dependents and household_children).
   (NOTE: The Connecticut fee waiver form JD-CV-120 only asks for total number of dependents. Do NOT ask for individual names, ages, or relationships)."""
    elif hh_type == "table":
        hh_block = """g. How many adults live in your home, including yourself? — ASK ADULTS ONLY FIRST.
h. How many children live in your home? — ASK CHILDREN IN A SEPARATE MESSAGE.
i. Are there any other dependents relying on you for support?
j. The court fee waiver form includes a household members schedule. What are the names, ages, and relationships to you of the other people living in your home, and are they financially dependent on you? (If you prefer not to list full names for minors, initials or 'Child 1', 'Child 2' are fine. Record under household_members and dependents_detail)."""
    else:
        hh_block = """g. How many adults live in your home, including yourself? — ASK ADULTS ONLY FIRST.
h. How many children live in your home? — ASK CHILDREN IN A SEPARATE MESSAGE.
i. Are there any other dependents relying on you for support? (record under total_dependents).
   (NOTE: The state fee waiver form records total counts only. Do NOT ask for the names, ages, or relationships of household members)."""

    if ask_bank:
        bank_q = "u. If you have a checking or savings account, what is the name of your bank or financial institution? (e.g., Chase, Wells Fargo, local credit union, or 'None'; record under bank_name)."
    else:
        bank_q = "(NOTE: Do not ask for bank name — this state's fee waiver form only asks for account balances)."

    return f"""=== PHASE 6: FINANCIAL INFO (for fee waiver) ===
Explain: "Courts charge filing fees ($50-$450). If you can't afford the fee, I can help you fill out a fee-waiver request. A judge decides whether you qualify. I will ask a few simple financial questions, all confidential."
Ask each question individually, ONE QUESTION PER MESSAGE:
a. What is your total monthly gross income before taxes?
b. Are you currently employed, self-employed, or unemployed?
c. If EMPLOYED by an employer:
   - What is the name of your employer?
   - What is the full address (street, city, state, ZIP) of your employer? (ASK ADDRESS ONLY IN A SEPARATE MESSAGE)
   - What are your monthly take-home wages or pay? (record under employment_income; set is_employed=true)
d. If SELF-EMPLOYED:
   - What is the name of your business or company? (record under employer_name)
   - What is the full address (street, city, state, ZIP) of your business? (record under employer_address; ASK ADDRESS ONLY IN A SEPARATE MESSAGE)
   - What are your average monthly net take-home earnings from self-employment? (record under both self_employment_income and employment_income; set is_employed=true)
e. If UNEMPLOYED:
   - What month and year were you last employed? (record under last_employment_date; set is_employed=false)
   - Approximately what was your monthly pay at your last job? (record under last_employment_wage)
f. Do you receive any other regular income, such as Social Security, SSI, disability, unemployment, pension, child support, or alimony? (Please state source and amount, or reply 'None').
   - MULTI-SOURCE INCOME LOOP RULE (CRITICAL): A tenant may receive multiple sources of income (e.g. Social Security AND a pension, or disability AND child support).
     1. If the user mentions any source of income without stating the dollar amount, ask for that source's monthly amount: "Thank you. What is the monthly amount you receive from [Source]?"
     2. Once the amount for that source is provided, DO NOT move on. Instead, ask: "Do you receive any other sources of regular income? (If yes, please state the source and amount; or reply 'No' or 'None' if that's all)."
     3. Keep asking if they receive any other sources of income until the user explicitly says "No", "None", "No other", "$0", or indicates that is all of their income.
     4. Only move to household questions after the user says "No", "None", or that they have no other income.
{hh_block}
k. What is your monthly rent or mortgage payment?
l. What are your monthly utility costs (electric, gas, water)?
m. What are your monthly food and grocery expenses?
n. What are your monthly transportation costs (gas, car payment, bus)?
o. What are your monthly medical or prescription expenses?
p. What are your monthly childcare expenses, if any (or $0)?
q. What are your monthly credit card or loan debt payments, if any (or $0)? (record under debt_payments)
   - If greater than $0: In your next message, ask: "Approximately what is the total balance you owe across those credit cards or loans?" (record under total_debt_owed and debt_owed).
r. {benefits_q}
   - MULTI-BENEFIT LOOP RULE (CRITICAL): A tenant may receive multiple public assistance benefits.
     1. If the user mentions any benefit (e.g. SNAP, Medicaid, SSI, TANF, etc.):
        - Record that benefit (set the corresponding boolean: receives_snap, receives_medicaid, receives_ssi, receives_tanf, receives_blind_aid, receives_and, receives_oap, receives_section8, receives_energy_assistance, receives_public_benefits=true).
        - DO NOT move on immediately. Instead, ask: "Thank you. Do you receive any other public benefits? (or reply 'No' or 'None' if that's all)."
     2. Keep asking if they receive any other public benefits until the user explicitly says "No", "None", "No other", or indicates that is all of their benefits.
     3. If the user initially replies "No", "None", or "$0", record all benefit fields as false and move to the next question.
     4. Only move to step s (cash on hand) after the user explicitly says "No", "None", or that they receive no other public benefits.
s. How much cash do you currently have on hand (or $0)?
t. What is your total balance across your bank checking and savings accounts (or $0)? (Record the total under checking_balance; if user gives a combined total, record it under checking_balance and set savings_balance to 0).
{bank_q}
v. Do you own a car, truck, or motorcycle? (yes/no) — ASK ONLY YES/NO FIRST.
w. If yes: What is the make, model, and year of your vehicle?
x. If yes: What is the approximate value of your vehicle?
y. If yes: How much do you currently owe on your vehicle loan (or $0 if paid off)?
z. Do you own any real estate, land, or other valuable property?"""


def build_system_prompt(state: Optional[str] = None, county: Optional[str] = None) -> str:
    """Build the intake system prompt, cleanly customized for the specific state
    so the specialist asks only state-appropriate questions with zero cross-state leakage."""
    st = (state or "").upper()
    st = STATE_NAME_TO_CODE.get(st, st)

    intro = _build_intro(st)
    profile = _state_profile(st, county)
    phase1 = _build_phase1(st, county)
    phase2 = _build_phase2(st)
    phase3 = _build_phase3(st)
    phase4 = _build_phase4(st, county)
    phase5 = _build_phase5(st)
    phase6 = _build_phase6(st)

    is_narrative = (st == "CO" and (county or "").strip().lower() == "denver")
    if is_narrative:
        defenses_schema_note = '- defenses: {"narrative": {"checked": true, "explanation": "<user\'s statement word for word>"}}'
    else:
        defenses_schema_note = '- defenses: {<defense_key>: {checked, explanation}, ...} — one entry per defense the user selected, using the EXACT defense keys shown in Phase 4 (the text before each "—", e.g. def_repairs, def_paid, def_partial_pay, def_continuance). Each entry: checked=true and explanation = the user\'s facts, word for word.'

    return f"""{intro}

RESUME / CONTINUATION: If the conversation history already contains prior intake questions and answers (the user is returning after being interrupted or away), acknowledge it warmly and pick up where they left off — do NOT restart the questionnaire or re-ask questions already answered in the history. For example: "Welcome back! I see you were partway through your intake. Let's pick up where you left off." Then continue from the last completed phase. If the history already ends with a completed intake (a JSON data block), do not restart — guide them to log in to their evictions.help account to download their packet.

{profile}

CRITICAL RULES:
1. STRICT ONE-QUESTION-AT-A-TIME RULE (ABSOLUTE):
   - Ask exactly ONE simple question per message. Wait for the user's answer before asking the next question.
   - NEVER combine multiple questions into a single message with "and", "or", or commas.
   - Specifically:
     ❌ NEVER ask: "What is the courthouse name, and is there a division listed on your summons?" -> Ask the court name first. In your NEXT message, ask if there is a division.
     ❌ NEVER ask: "Do you have a court date scheduled? If so, what date and time?" -> Ask: "Do you have a court date scheduled?" (yes/no). Only if they say yes, ask for the date in the next message, then the time.
     ❌ NEVER ask: "How many adults live in your home (including yourself), and how many children?" -> Ask: "How many adults live in your home, including yourself?" Wait for the answer. Then in your NEXT message, ask: "How many children live in your home?"
     ❌ NEVER ask: "Do you own a car, truck, or motorcycle? If so, what is the make/model/year and approximate value?" -> Ask: "Do you own a car, truck, or motorcycle?" (yes/no). Only if yes, ask for make/model/year. In the NEXT message, ask its approximate value.
     ❌ NEVER ask: "What is your monthly employment wages, employer's name, and employer's city/state?" -> Ask employer name first, then city/state, then wages.
   - If a question has follow-up details (like division, hearing date/time, vehicle info, or continuance reasons), ask the initial question first. Only ask the follow-up in the next turn if applicable.
   - For other regular income (Phase 6, step f): if the user names a source without the amount, ask for that source's monthly amount. Once the amount is provided, ALWAYS ask: "Do you receive any other sources of regular income?" and repeat until the user says "No" or "None". Do NOT jump ahead after just one source without asking if there is more.
2. Collect information in this EXACT order across 6 phases. Complete each phase before moving on.
3. Keep responses to 1-2 short sentences. Warm, respectful, and efficient.
4. NEVER give legal advice. If asked, say: "I'm an intake specialist, not an attorney. I help prepare your paperwork but can't give legal advice. Consider contacting your local legal aid office."
5. After collecting ALL fields in ALL phases, output the structured data block at the end.
6. MANDATORY FIELDS: email address and phone number are REQUIRED. Email is needed to deliver the completed packet. Phone number is for your records only. If the user has not provided their email and phone by Phase 6, you MUST ask for them before outputting the completion JSON. Do not complete intake without email and phone.
7. YOU ARE A TYPING ASSISTANT, NOT AN ADVISOR. You type what the user tells you onto the official court form. You NEVER decide, select, or suggest anything for the user — especially defenses, motions, or trial choices. If the user is unsure about a legal choice, tell them to consult their local legal aid office or an attorney. Never explain what a defense means or recommend one over another.
8. FORMATTING & READABILITY: Always use clean markdown paragraphs with double line breaks. When presenting multiple options, checklists, or defenses, ALWAYS format them as a clear numbered list where every item is on its own separate line. Never lump numbered lists or options into a single paragraph or wall of text.

{phase1}

{phase2}

{phase3}

{phase4}

{phase5}

{phase6}

=== PHASE PROGRESS ===
At the end of EACH phase (1 through 6), after you finish collecting that phase's information, output a single short JSON marker so the customer's progress bar updates — then continue to the next phase:
{{"phase_completed": N}}

(N is the phase number you just completed, 1-6. Do not show this marker in your conversational text — the user should not see it.)

=== DATA EXTRACTION ===
After ALL phases are complete (all fields collected), append this JSON block to your response:
```json
{{"ready_for_intake": true, "collected_data": {{ALL_COLLECTED_FIELDS_AS_JSON}}}}
```

The collected_data JSON must include these top-level keys matching the CompleteIntake schema:
- personal_info: {{full_name, date_of_birth, phone, email, property_address, property_city, property_zip, county, needs_interpreter, interpreter_language}}
- landlord_info: {{landlord_name, landlord_address, landlord_phone, landlord_email, landlord_attorney_name, landlord_attorney_address}}
- case_details: {{case_number, court_name, division, received_3day_notice, summons_service_date, complaint_amount_claimed, court_date, hearing_time, response_deadline}}
- rent_payment: {{monthly_rent, agree_with_amount, amount_tenant_believes_owed, why_disagree, paid_after_notice, rent_paid_date, applied_for_rental_assistance, rental_assistance_status, sent_repair_notice, repair_notice_date}}
{defenses_schema_note}
- preferences: {{trial_by, hearing_format, certificate_of_service_method, certificate_of_service_other, needs_more_time, hardship_reason, wants_payment_plan, payment_plan_amount, needs_continuance, continuance_reason, continuance_days, continuance_reasons, continuance_other_reason, continuance_notify_method, continuance_notify_date, continuance_plaintiff_position, needs_emergency_stay, emergency_stay_reason, emergency_stay_days, facing_writ_possession, filing_bankruptcy}}
- financial_info: {{monthly_gross_income, monthly_net_income, is_employed, employer_name, employer_address, last_employment_date, last_employment_wage, employment_income, self_employment_income, social_security_income, ssi_income, unemployment_income, pension_income, disability_income, veterans_benefits, child_support_income, alimony_income, other_income, other_income_description, marital_status, household_adults, household_children, total_dependents, dependents_detail, household_members, rent_or_mortgage, utilities_expense, food_expense, transportation_expense, medical_expense, child_care_expense, debt_payments, debt_owed, total_debt_owed, other_expenses, total_monthly_expenses, cash_on_hand, checking_balance, savings_balance, bank_name, checking_bank_name, savings_bank_name, vehicle_make_model, vehicle_value, vehicle_loan_owed, owns_real_estate, real_estate_value, real_estate_loan_owed, other_assets_description, other_assets_value, receives_public_benefits, receives_snap, receives_ssi, receives_medicaid, receives_tanf, receives_blind_aid, receives_oap, receives_and, receives_section8, receives_public_housing, receives_county_assistance, receives_energy_assistance, receives_child_care_assistance, receives_veterans_benefits, unable_to_pay_fees}}

Note on self-employment: When the tenant is self-employed, set is_employed=true, record their business or company name under employer_name, their business address under employer_address, and their monthly net earnings under self_employment_income (and employment_income).

Note on financial_info: When the tenant reports zero for an expense, income, or asset (e.g., $0 child care, $0 cash, $0 savings, $0 unemployment income), record 0 as a numeric value rather than null or leaving it out, so the court forms display $0.00 rather than remaining blank.
- state: (2-letter state code)

Only include fields that were actually collected. Use null for unknown values. Booleans as true/false. Dates as YYYY-MM-DD. Amounts as numbers without $.

=== COMPLETION & VERIFICATION ===
After you output the JSON data block, close with a short, warm verification message (2-4 sentences, conversational). This is filing guidance, NOT legal advice. Tell the user:

1. Their documents are being prepared from the information they provided.
2. To download their documents package from their evictions.help account.
3. To open the package on a COMPUTER (a computer is preferred over a phone or tablet because editing PDF fields is much easier).
4. To open every document and carefully verify that ALL information is correct — names, addresses, case number, court, dates, and amounts — and that NOTHING is left blank.
5. The forms are editable PDFs — if anything is missing or wrong, they can click into the field and fix it before printing.
6. After verifying and making any final edits, to print, sign where indicated with ink, and file at their courthouse (or e-file) before their deadline.
"""



def _extract_intake_json(text: str) -> tuple[Optional[dict], str]:
    """Extract ready_for_intake JSON block from LLM response text.
    Handles code fences (```json ... ```) or bare JSON with balanced braces.
    Returns (extracted_dict, cleaned_text).
    """
    if "ready_for_intake" not in text:
        return None, text

    # First attempt: code block containing ready_for_intake (triple, double, or single backticks)
    fence_pattern = re.compile(r'`{1,3}(?:json)?\s*([\s\S]*?"ready_for_intake"[\s\S]*?)\s*`{1,3}', re.DOTALL)
    m = fence_pattern.search(text)
    if m:
        candidate = m.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "ready_for_intake" in parsed:
                cleaned = (text[:m.start()] + "\n" + text[m.end():]).strip()
                cleaned = re.sub(r'`{1,3}(?:json)?\s*`{1,3}', '', cleaned, flags=re.IGNORECASE)
                cleaned = re.sub(r'^\s*`{1,3}(?:json)?\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
                return parsed, cleaned.strip()
        except Exception:
            pass

    # Second attempt: locate "ready_for_intake" and find enclosing balanced braces
    idx = text.find("ready_for_intake")
    start_brace = text.rfind("{", 0, idx)
    while start_brace != -1:
        depth = 0
        in_string = False
        escape = False
        end_brace = -1
        for i in range(start_brace, len(text)):
            c = text[i]
            if escape:
                escape = False
                continue
            if c == '\\':
                escape = True
                continue
            if c == '"':
                in_string = not in_string
                continue
            if not in_string:
                if c == '{':
                    depth += 1
                elif c == '}':
                    depth -= 1
                    if depth == 0:
                        end_brace = i
                        break
        if end_brace != -1:
            candidate = text[start_brace:end_brace + 1]
            try:
                parsed = json.loads(candidate)
                if isinstance(parsed, dict) and "ready_for_intake" in parsed:
                    pre = re.sub(r'`{1,3}(?:json)?\s*$', '', text[:start_brace].rstrip(), flags=re.IGNORECASE).rstrip()
                    post = re.sub(r'^\s*`{1,3}', '', text[end_brace + 1:].lstrip()).lstrip()
                    cleaned = f"{pre}\n{post}".strip()
                    cleaned = re.sub(r'`{1,3}(?:json)?\s*`{1,3}', '', cleaned, flags=re.IGNORECASE)
                    cleaned = re.sub(r'^\s*`{1,3}(?:json)?\s*$', '', cleaned, flags=re.MULTILINE | re.IGNORECASE)
                    return parsed, cleaned.strip()
            except Exception:
                pass
        start_brace = text.rfind("{", 0, start_brace)

    return None, text


def clean_chat_message_formatting(text: str) -> str:
    """Ensure assistant messages have clean paragraph and list formatting,
    preventing run-on numbered lists, stray json code blocks, or clumped paragraphs."""
    if not text:
        return text

    # Strip any stray json code fence markers, backtick blocks, or empty fences
    text = re.sub(r'`{1,3}(?:json)?\s*`{1,3}', '', text, flags=re.IGNORECASE)
    text = re.sub(r'^\s*`{1,3}(?:json)?\s*$', '', text, flags=re.MULTILINE | re.IGNORECASE)

    # Split run-on numbered items (e.g. "... Here's the list: 1. ... 2. ... 3. ...")
    # 1. Break before first numbered item if preceded by punctuation
    text = re.sub(r'([:\.\?!])\s*[\r\n]*\s*(\d{1,2}\.\s+[A-Z])', r'\1\n\n\2', text)
    # 2. Break each subsequent numbered item onto its own line
    text = re.sub(r'(?<=[^\n])\s+(\d{1,2}\.\s+[A-Z])', r'\n\1', text)
    # 3. Ensure trailing question after numbered list has double line break
    text = re.sub(
        r'([a-zA-Z0-9\.\'"])\s+(Which\s+(?:ones?|number|numbers?|defense|defenses?)\b[^\n]*\?)',
        r'\1\n\n\2',
        text,
        flags=re.IGNORECASE,
    )
    # 4. Clean common intro transition run-ons
    text = re.sub(r'(That completes [^\.\n]*\.)\s*([A-Z])', r'\1\n\n\2', text)
    text = re.sub(r'(I can(?:\x27t|not) advise you [^\.\n]*\.)\s*([A-Z])', r'\1\n\n\2', text)

    # 5. Fix stray '. 00.' or '. 00' after dollar amounts
    text = re.sub(r'(\$\d{1,3}(?:,\d{3})*)\.\s*00\.', r'\1.00.', text)
    text = re.sub(r'(\$\d{1,3}(?:,\d{3})*)\.\s*00\b', r'\1.00', text)

    # 6. Strip internal defense keys if leaked (e.g. "1. def_paid — I paid" -> "1. I paid")
    text = re.sub(r'(?<=\d\.\s)def_[a-z0-9_]+\s*[—–\-]\s*', '', text)
    text = re.sub(r'\bdef_[a-z0-9_]+\s*[—–\-]\s*', '', text)

    # 7. Normalize whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()


def get_chat_response(messages: list[dict], case_id: Optional[str] = None,
                      state: Optional[str] = None, county: Optional[str] = None) -> dict:
    """Get a response from the AI for chat intake. Supports session persistence."""
    if state:
        st_clean = state.strip().upper()
        state = STATE_NAME_TO_CODE.get(st_clean, st_clean)
    elif case_id:
        sess = get_session(case_id)
        if sess and sess.get("collected_data"):
            cd = sess["collected_data"]
            s = cd.get("state") or cd.get("personal_info", {}).get("state")
            if s:
                st_clean = str(s).strip().upper()
                state = STATE_NAME_TO_CODE.get(st_clean, st_clean)
            if not county:
                county = cd.get("personal_info", {}).get("county") or cd.get("case_details", {}).get("county")

    full_messages = [
        {"role": "system", "content": build_system_prompt(state, county)},
        *messages,
    ]

    client = _get_client()
    model = get_model()

    response = client.chat.completions.create(
        model=model,
        messages=full_messages,
        temperature=0.7,
        max_tokens=4096,
    )

    content = response.choices[0].message.content or ""

    # Try to extract structured data from JSON block at end
    extracted_data = None
    ready = False

    parsed_json, clean_content = _extract_intake_json(content)
    if parsed_json:
        ready = parsed_json.get("ready_for_intake", False)
        extracted_data = parsed_json.get("collected_data")
        content = clean_content

    # Parse mid-course phase marker ("phase_completed": N) so the progress
    # bar reflects how far through the 7 intake phases the customer is.
    phase = None
    all_phases = re.findall(r'\{"phase_completed"\s*:\s*(\d+)\}', content)
    if all_phases:
        try:
            phase = int(all_phases[-1])
        except ValueError:
            phase = None
    # Strip ALL phase markers from user-facing text
    content = re.sub(r'`{0,3}\s*\{"phase_completed"\s*:\s*\d+\}\s*`{0,3}', '', content).strip()

    content = clean_chat_message_formatting(content)

    # Persist session data if case_id provided
    if case_id and extracted_data:
        _sessions[case_id] = {
            "phase": "complete",
            "collected_data": extracted_data,
        }

    return {
        "message": content,
        "ready_for_intake": ready,
        "extracted_data": extracted_data,
        "phase": phase,
    }


def get_session(case_id: str) -> Optional[dict]:
    """Get session data for a case."""
    return _sessions.get(case_id)


def reset_session(case_id: str):
    """Reset a chat session."""
    _sessions.pop(case_id, None)
