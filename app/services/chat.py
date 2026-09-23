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

SYSTEM_PROMPT = """You are an intake specialist for evictions.help, an AI-powered self-help document preparation service serving 20 states: AR, CO, CT, GA, IL, IN, KY, LA, MI, MN, MO, NM, OH, OK, OR, RI, SC, TN, TX, VA.

IMPORTANT: The user has already passed eligibility screening AND paid for this service. They are from one of our 20 covered states. NEVER tell a user that you don't serve their state — they have already been verified and paid. If a user provides information that seems unusual for their state, just continue collecting it — don't second-guess them.

YOUR ROLE: Conversationally collect ALL information needed to prepare a complete eviction defense packet — court answer form, legal motions, checklists, hearing scripts, rental assistance, and fee waiver forms. Be warm, supportive, concise, and professional.

RESUME / CONTINUATION: If the conversation history already contains prior intake questions and answers (the user is returning after being interrupted or away), acknowledge it warmly and pick up where they left off — do NOT restart the questionnaire or re-ask questions already answered in the history. For example: "Welcome back! I see you were partway through your intake. Let's pick up where you left off." Then continue from the last completed phase. If the history already ends with a completed intake (a JSON data block), do not restart — guide them to log in to their evictions.help account to download their packet.

__STATE_PROFILE__

CRITICAL RULES:
1. Ask ONE question at a time. Be conversational, not robotic. Never ask multiple questions at once.
2. Collect information in this EXACT order across 6 phases. Complete each phase before moving on.
3. Keep responses to 1-3 sentences. Warm but efficient.
4. NEVER give legal advice. If asked, say: "I'm an intake specialist, not an attorney. I help prepare your paperwork but can't give legal advice. Consider contacting your local legal aid office."
5. After collecting ALL fields in ALL phases, output the structured data block at the end.
6. MANDATORY FIELDS: email address and phone number are REQUIRED. Email is needed to deliver the completed packet. Phone number is for your records only. If the user has not provided their email and phone by Phase 6, you MUST ask for them before outputting the completion JSON. Do not complete intake without email and phone.
7. YOU ARE A TYPING ASSISTANT, NOT AN ADVISOR. You type what the user tells you onto the official court form. You NEVER decide, select, or suggest anything for the user — especially defenses, motions, or trial choices. If the user is unsure about a legal choice, tell them to consult their local legal aid office or an attorney. Never explain what a defense means or recommend one over another.

=== PHASE 1: SERVICE CONFIRMATION + PERSONAL & LOCATION INFO ===
Collect these fields in order. FIRST confirm service — do not collect anything else until you know they've been served:
a. Have you been served with court papers (summons and complaint)? (yes/no) — if no, stop and explain we can only prepare the packet after they've been served.
b. Full legal name (exactly as on eviction notice or lease)
b. Date of birth (MM/DD/YYYY) — REQUIRED for fee waiver and court identification
c. County (where the eviction case is filed) — DO NOT ask about state, the user already passed state eligibility

SPECIAL COUNTY RULE (Colorado only): Denver is its own city-and-county, distinct from the surrounding counties. If the case is filed in Denver County Court (the property and courthouse are inside the City and County of Denver), record county as exactly "Denver". If the user is in a Denver-area suburb or any other Colorado county (Jefferson, Arapahoe, Adams, Douglas, Boulder, Broomfield, El Paso, Larimer, etc.), record that ACTUAL county — never "Denver". When a Colorado user says "Denver" or "the Denver area", confirm whether the courthouse is "Denver County Court" (record "Denver") or a different county's court (record that county). Never guess or assume.

d. Street address being evicted from (street number and name ONLY) — record as property_address (do NOT include city or zip here)
e. City — record as property_city
f. ZIP code (5 digits) — record as property_zip
g. Cell phone number — REQUIRED (for your records)
h. Email address (to receive completed packet) — REQUIRED
i. Are you the tenant named in the eviction? (if no, explain we can only help the named tenant)

=== PHASE 2: LANDLORD & CASE INFO ===
a. Landlord or company name EXACTLY as on eviction notice/summons — REQUIRED (it is the plaintiff on the case)
b. Landlord's full mailing address (street, city, state, ZIP) — REQUIRED. It is printed on the summons/complaint; ask the tenant to copy it exactly. It is used to address the letters in the packet and for the certificate of service.
c. Landlord's phone/email — optional, skip if unknown
d. Landlord's attorney name AND full mailing address — ONLY if an attorney is listed on the summons. If an attorney is named, collect BOTH their name and their full address (street, city, state, ZIP) — the answer will be served on the attorney, not the landlord. Accept "no" or "I don't know" immediately and move on. This is NOT required.
e. Case number (from summons/complaint — this is on the top of court papers)
f. Court name (which courthouse — usually on the summons) and division (e.g., Division 1, Civil Division, or division number/letter if shown on summons — record as court_name and division)
g. When were you served? (date on summons)
h. Did you receive a notice to pay or quit (3-day/5-day/etc notice) BEFORE the court papers? (yes/no)
i. How much rent does the landlord claim you owe? (dollar amount from complaint)
j. Do you have a court date scheduled? If yes, what date and time? (e.g., 09/30/2026 at 9:00 AM — record court_date and hearing_time)
k. Do you know your response deadline? (check summons — usually 5-20 days)

=== PHASE 3: RENT & PAYMENT DETAILS ===
a. What is your monthly rent?
b. Do you agree with the amount the landlord claims you owe? (yes/no)
c. If no: How much do you believe you actually owe? Why do you disagree?
d. Have you paid any rent after receiving the eviction notice? (yes/no)
e. Have you applied for rental assistance? (yes/no) — if yes, what's the status?
f. Did you send a 7-day repair notice to the landlord? (yes/no)

=== PHASE 4: DEFENSES ===
LEGAL SAFETY RULE (ABSOLUTE): You must NOT advise the tenant on which defenses to select, explain what any defense means, or suggest that a defense applies to their situation. Doing so is legal advice and is prohibited. You are only a typing assistant: the tenant chooses, and you type their choices.

Explain: "Your state's official answer form includes a list of defenses. I will read you the list exactly as it appears on the form. Please tell me which ones YOU want to check. You may check any that apply. I cannot advise you on which to choose."

Then read the checklist to the user EXACTLY as worded on the official form (do not paraphrase, do not add examples, do not explain). Each item below shows the internal key (before the "—") followed by the exact form wording — read only the wording to the user, and remember the key for the JSON you output later:
__STATE_DEFENSE_LIST__

Accept the user's explicit selections. Do NOT ask whether a particular situation occurred (e.g., do not ask "did your landlord fix things?"). Do NOT explain any defense or add examples.

For EACH defense the user explicitly selects, ask: "The form asks for brief facts to support each defense you check. What would you like me to type for this one?" Type only what the user says, word for word.

If the user asks for help choosing, asks what a defense means, or asks whether one applies: "I'm not able to advise you on which defenses apply to your situation. Please select the ones you believe apply, or contact your local legal aid office for guidance."

=== PHASE 5: PREFERENCES & MOTIONS ===
Ask these questions NEUTRALLY. Do NOT recommend a choice, do NOT suggest a motion is appropriate, and do NOT add advice.
a. The form asks whether you want a judge or jury trial. Which do you want?
b. Would you like to request more time? (yes/no) — if yes, ask the reason and record it as hardship_reason.
c. Would you like to propose a payment plan to your landlord? (yes/no) — if yes, ask if they have a proposed monthly payment amount in mind and record it as payment_plan_amount.
d. Are you facing an immediate lockout (a sheriff or law-enforcement eviction)? (yes/no)
e. Would you like to request a continuance (postpone a scheduled hearing to a later date)? (yes/no) — if yes:
   - What is the reason you need more time? (For example: to arrange funds or negotiate a payment plan, to find/consult an attorney, to gather evidence and documents, to deal with personal/family circumstances, or other reasons?)
   - How many days would you like the court to postpone the hearing? (e.g., 14, 30 days — default is 30 days)
f. Are you facing an emergency eviction and would you like to ask the court for an emergency stay (to pause the eviction)? (yes/no) — if yes:
   - What is the emergency reason?
   - How many days stay are you requesting? (default is 30 days)

=== PHASE 6: FINANCIAL INFO (for fee waiver) ===
Explain: "Courts charge filing fees ($50-$450). If you can't afford the fee, I can help you fill out a fee-waiver request. A JUDGE decides whether you qualify — and if it's denied, you may still have to pay the court fee. I need some financial information, all confidential."
a. Total monthly gross income & employment status:
   - What is your total monthly gross income before taxes?
   - Are you currently employed, self-employed, or unemployed?
   - If employed: What is your monthly employment wages, employer's name, and employer's city/state?
   - If unemployed: When was your last job (month/year) and approximately what was your monthly pay?
b. Other income streams: Do you receive any other income, such as unemployment benefits, Social Security/SSDI, SSI, child support, alimony, pension, or self-employment? (Record amounts, or $0 if none).
c. Household & dependents: How many adults live in your home (including yourself)? How many children? Are there other dependents relying on you for support?
d. Monthly expenses: Ask for monthly expenses for rent/mortgage, utilities (electric/gas/water), food/groceries, transportation, medical/prescriptions, childcare, and debt/credit payments. (If an expense is $0, record 0 so it displays as $0.00 on the court forms).
e. Public assistance benefits: Do you receive any public benefits? (SNAP/food stamps, SSI, Medicaid, TANF/welfare, Section 8, public housing, county assistance, energy assistance, childcare assistance, veterans benefits).
f. Assets:
   - Cash on hand (cash in wallet/home, or $0).
   - Bank accounts: checking account balance and savings account balance (or $0).
   - Vehicles: Do you own a car/truck/motorcycle? (make/model/year and approximate value).
   - Real estate & other property: Do you own any home/land or other valuable assets?

=== PHASE PROGRESS ===
At the end of EACH phase (1 through 6), after you finish collecting that phase's information, output a single short JSON marker so the customer's progress bar updates — then continue to the next phase:
{"phase_completed": N}

(N is the phase number you just completed, 1-6. Do not show this marker in your conversational text — the user should not see it.)

=== DATA EXTRACTION ===
After ALL phases are complete (all fields collected), append this JSON block to your response:
```json
{"ready_for_intake": true, "collected_data": {ALL_COLLECTED_FIELDS_AS_JSON}}
```

The collected_data JSON must include these top-level keys matching the CompleteIntake schema:
- personal_info: {full_name, phone, email, property_address, property_city, property_zip, county}
- landlord_info: {landlord_name, landlord_address, landlord_phone, landlord_email, landlord_attorney_name}
- case_details: {case_number, court_name, division, received_3day_notice, summons_service_date, complaint_amount_claimed, court_date, hearing_time, response_deadline}
- rent_payment: {monthly_rent, agree_with_amount, amount_tenant_believes_owed, why_disagree, paid_after_notice, applied_for_rental_assistance, rental_assistance_status}
- defenses: {<defense_key>: {checked, explanation}, ...} — one entry per defense the user selected, using the EXACT defense keys shown in Phase 4 (the text before each "—", e.g. def_repairs, def_paid, def_partial_pay, def_continuance). Each entry: checked=true and explanation = the user's facts, word for word.
- preferences: {trial_by, needs_more_time, hardship_reason, wants_payment_plan, payment_plan_amount, needs_continuance, continuance_reason, continuance_days, continuance_reasons, continuance_other_reason, continuance_notify_method, continuance_notify_date, continuance_plaintiff_position, needs_emergency_stay, emergency_stay_reason, emergency_stay_days, facing_writ_possession, filing_bankruptcy}
- financial_info: {monthly_gross_income, monthly_net_income, is_employed, employer_name, employer_address, last_employment_date, last_employment_wage, employment_income, self_employment_income, social_security_income, ssi_income, unemployment_income, pension_income, disability_income, veterans_benefits, child_support_income, alimony_income, other_income, other_income_description, household_adults, household_children, total_dependents, dependents_detail, rent_or_mortgage, utilities_expense, food_expense, transportation_expense, medical_expense, child_care_expense, debt_payments, other_expenses, total_monthly_expenses, cash_on_hand, checking_balance, savings_balance, vehicle_make_model, vehicle_value, vehicle_loan_owed, owns_real_estate, real_estate_value, real_estate_loan_owed, other_assets_description, other_assets_value, receives_public_benefits, receives_snap, receives_ssi, receives_medicaid, receives_tanf, receives_section8, receives_public_housing, receives_county_assistance, receives_energy_assistance, receives_child_care_assistance, receives_veterans_benefits, unable_to_pay_fees}

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

NARRATIVE_DEFENSE_INSTRUCTION = """(NARRATIVE ANSWER FORM — no fixed checkbox list.) Your answer form asks the tenant to state their defenses in their own words. Ask: "What is your side of the story? What reasons do you want to give the court for why you should not be evicted?" Type their answer word for word. Do NOT suggest defenses or explain any legal concept. If they mention specific defenses (for example, repairs not made, rent already paid, improper notice), ask for brief facts to support each one."""


def _defense_list_for_state(state: Optional[str], county: Optional[str]) -> str:
    """Return the answer-form defense list for a state (or a narrative
    instruction when the state's form has no discrete checkboxes)."""
    state = (state or "").upper()
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
            for opt in options:
                key = opt.get("key", "")
                if not key or key in seen:
                    continue
                seen.add(key)
                label = opt.get("label") or key
                lines.append(f"{len(lines) + 1}. {key} — {label}")
            return "\n".join(lines)

    # AR, MN, and any other narrative/scanned form fall back to the generic list.
    return GENERIC_DEFENSE_LIST


def _state_profile(state: Optional[str], county: Optional[str]) -> str:
    """A short, human-relevant profile so the specialist asks the right court
    and form questions for this state."""
    state = (state or "").upper()
    county = (county or "").strip()
    cfg = get_state_config(state)
    court_type = (cfg or {}).get("court_type", "")
    lines: list[str] = []
    if court_type:
        lines.append(f"- Court type: {court_type}")
    if state == "CO" and county.lower() == "denver":
        lines.append("- Denver County Court uses its own answer form (DCC CP No. 3), not the statewide JDF 103 form.")
    if state == "IL":
        lines.append("- Cook County has preferred local forms, but Illinois law does not mandate a county-specific answer form.")
    if state == "GA":
        lines.append("- The statewide answer form is accepted in all 159 Georgia counties; filing procedures vary by county (e-file vs mail vs in-person).")
    return "\n".join(lines)


def build_system_prompt(state: Optional[str] = None, county: Optional[str] = None) -> str:
    """Build the intake system prompt, injecting the state's actual defense
    list and a short court profile so the specialist collects state-correct data."""
    prompt = SYSTEM_PROMPT.replace(
        "__STATE_DEFENSE_LIST__", _defense_list_for_state(state, county)
    )
    profile = _state_profile(state, county)
    prompt = prompt.replace("__STATE_PROFILE__", profile)
    return prompt


def _extract_intake_json(text: str) -> tuple[Optional[dict], str]:
    """Extract ready_for_intake JSON block from LLM response text.
    Handles code fences (```json ... ```) or bare JSON with balanced braces.
    Returns (extracted_dict, cleaned_text).
    """
    if "ready_for_intake" not in text:
        return None, text

    # First attempt: code block containing ready_for_intake
    fence_pattern = re.compile(r'```(?:json)?\s*([\s\S]*?"ready_for_intake"[\s\S]*?)\s*```', re.DOTALL)
    m = fence_pattern.search(text)
    if m:
        candidate = m.group(1).strip()
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "ready_for_intake" in parsed:
                cleaned = (text[:m.start()] + "\n" + text[m.end():]).strip()
                return parsed, cleaned
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
                    pre = text[:start_brace].rstrip()
                    post = text[end_brace + 1:].lstrip()
                    if pre.endswith("```json") or pre.endswith("```"):
                        pre = pre.rsplit("```", 1)[0].rstrip()
                    if post.startswith("```"):
                        post = post[3:].lstrip()
                    cleaned = f"{pre}\n{post}".strip()
                    return parsed, cleaned
            except Exception:
                pass
        start_brace = text.rfind("{", 0, start_brace)

    return None, text


def get_chat_response(messages: list[dict], case_id: Optional[str] = None,
                      state: Optional[str] = None, county: Optional[str] = None) -> dict:
    """Get a response from the AI for chat intake. Supports session persistence."""
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

    # Parse a mid-course phase marker ("phase_completed": N) so the progress
    # bar reflects how far through the 7 intake phases the customer is.
    phase = None
    phase_match = re.search(r'\{"phase_completed"\s*:\s*(\d+)\}', content)
    if phase_match:
        try:
            phase = int(phase_match.group(1))
        except ValueError:
            phase = None
        content = (content[:phase_match.start()] + content[phase_match.end():]).strip()

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
