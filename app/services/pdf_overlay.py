"""
PDF overlay system — fills any court form, even scanned/non-fillable PDFs.

For fillable PDFs: uses field mapping (fast, precise).
For scanned PDFs: overlays text at exact coordinates (works on any form).
"""

import os
import logging
from typing import Dict, Optional
from datetime import date

import fitz  # PyMuPDF

from app.services.state_configs import get_state_config

logger = logging.getLogger(__name__)

FORMS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")
REBUILT_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "rebuilt")


def _get_form_path(form_filename, state_code=""):
    """Get the best form to use — rebuilt version for overlay states, original for fillable."""
    if state_code:
        rebuilt_name = f"{state_code.lower()}_answer_rebuilt.pdf"
        rebuilt_path = os.path.join(REBUILT_DIR, rebuilt_name)
        if os.path.exists(rebuilt_path):
            # Only use rebuilt form if the original has NO fillable widgets (overlay/scanned)
            from app.services.state_configs import STATE_CONFIGS
            cfg = STATE_CONFIGS.get(state_code, {})
            if not cfg.get("has_fillable_fields", True):
                return rebuilt_path
    return os.path.join(FORMS_DIR, form_filename)


def fill_answer_form(data: dict, state: str, output_path: str) -> bool:
    """Fill a state's eviction answer form — handles fillable AND scanned PDFs."""
    return _fill_form(data, state, output_path, "answer_form")


def fill_fee_waiver(data: dict, state: str, output_path: str) -> bool:
    """Fill a state's fee waiver form."""
    return _fill_form(data, state, output_path, "fee_waiver_form")


def _fill_form(data: dict, state: str, output_path: str, form_key: str) -> bool:
    """Fill a state's form (answer or fee waiver) — handles fillable AND scanned PDFs."""
    state_code = state.upper()
    config = get_state_config(state_code)
    if not config:
        logger.warning(f"No state config for {state_code}")
        return False

    form_filename = config.get(form_key)
    if not form_filename:
        logger.warning(f"No form configured for {state_code} ({form_key})")
        return False

    # Use rebuilt form if available (clean standardized fields)
    form_path = _get_form_path(form_filename, state_code if form_key == "answer_form" else "")
    if not os.path.exists(form_path):
        logger.error(f"Form not found: {form_path}")
        return False

    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})

    doc = fitz.open(form_path)
    
    # Check if form has fillable fields
    has_fields = False
    try:
        widgets_list = list(doc.load_page(0).widgets())
        fields_count = len(widgets_list)
        has_fields = fields_count > 0
    except Exception:
        pass

    has_overlay = bool(config.get("overlay_positions"))
    # For fee waiver forms, also check fee_waiver_overlay
    if form_key == "fee_waiver_form":
        has_overlay = has_overlay or bool(config.get("fee_waiver_overlay"))
    # Also check fee_waiver_mapping for fillable fee waiver PDFs
    if form_key == "fee_waiver_form" and config.get("fee_waiver_mapping"):
        has_fields = True  # Treat as fillable if mapping exists
    
    if has_fields and has_overlay:
        # Hybrid: both fillable fields AND overlay positions
        _fill_via_widgets(doc, data, config)
        _fill_via_overlay(doc, data, config, form_key)
    elif has_fields:
        _fill_via_widgets(doc, data, config)
    else:
        _fill_via_overlay(doc, data, config, form_key)

    doc.save(output_path, deflate=True)
    doc.close()
    logger.info(f"✅ {state_code} form saved: {output_path}")
    return True


def _fill_via_widgets(doc: fitz.Document, data: dict, config: dict):
    """Fill a PDF's form fields using widget/field mapping + smart auto-fill."""
    mapping = config.get("field_mapping", {})
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    today = date.today()
    
    values = {}
    
    # === UNIFIED MAPPING FOR REBUILT FORMS (standardized field names) ===
    # These work for ALL states with rebuilt forms — predictable, clean field names
    UNIFIED_MAP = {
        "defendant_name": p.get("full_name", ""),
        "plaintiff_name": l.get("landlord_name", ""),
        "case_number": c.get("case_number", ""),
        "court_name": c.get("court_name", ""),
        "county": p.get("county", ""),
        "property_address": p.get("property_address", ""),
        "phone": p.get("phone", ""),
        "email": p.get("email", ""),
        "date": today.strftime("%m/%d/%Y"),
        "printed_name": p.get("full_name", ""),
        "signature": "/s/",
        "rent_amount": str(c.get("monthly_rent", "")),
        "amount_claimed": str(c.get("complaint_amount_claimed", "")),
    }
    
    # Defense checkboxes — universal names
    DEFENSE_UNIFIED = {
        "def_repairs": "defense_repairs",
        "def_amount": "defense_amount",
        "def_attempted_pay": "defense_attempted_pay",
        "def_paid": "defense_paid",
        "def_waived": "defense_waived",
        "def_retaliation": "defense_retaliation",
        "def_fair_housing": "defense_discrimination",
        "def_accepted_rent": "defense_accepted_rent",
        "def_corrected": "defense_corrected",
        "def_not_owner": "defense_not_owner",
        "def_bad_notice": "defense_bad_notice",
        "def_other": "defense_other",
    }
    
    for chatbot_key, std_name in DEFENSE_UNIFIED.items():
        d = defenses.get(chatbot_key, {})
        checked = d.get("checked", False) if isinstance(d, dict) else False
        if checked:
            values[std_name] = "Yes"
    
    for std_name, val in UNIFIED_MAP.items():
        if val:
            values[std_name] = str(val)
    
    # Defense narrative
    if defenses:
        values["defense_narrative"] = _build_defense_narrative(defenses)
    
    # === LEGACY: Build _all_data for non-rebuilt forms that use field_mapping ===
    _all_data = {}
    for section in [p, l, c]:
        for k, v in section.items():
            if v:
                _all_data[k] = str(v)
    
    # Synthesize aliases — field_mapping keys must match _all_data keys
    aliases = {
        "full_name": ["name", "defendant_name", "printed_name"],
        "property_address": ["address", "street", "mailing_address", "property"],
        "property_city": ["city", "town"],
        "property_zip": ["zip", "postal_code"],
        "court_name": ["court_address", "courthouse", "court"],
        "landlord_name": ["plaintiff", "plaintiff_name", "landlord"],
        "phone": ["telephone", "phone_number", "cell"],
        "email": ["e_mail", "email_address"],
        "county": ["county_name"],
    }
    for source_key, target_keys in aliases.items():
        if source_key in _all_data:
            for tk in target_keys:
                if tk not in _all_data:
                    _all_data[tk] = _all_data[source_key]
    
    # Also add state-level data
    state_code = data.get("state", "")
    if state_code:
        _all_data["state"] = state_code
        _all_data["state_code"] = state_code
    
    # Certificate of Service mailing address — use property address as default
    if "cos_mail" not in _all_data and "property_address" in _all_data:
        _all_data["cos_mail"] = _all_data["property_address"]
    if "mailing_address" not in _all_data and "property_address" in _all_data:
        _all_data["mailing_address"] = _all_data["property_address"]
    
    # Certificate fields for CT, LA, and other states — derive from existing data
    cert_synthesis = {
        "cert_name": "full_name",
        "cert_address": "property_address", 
        "cert_date_signed": None,
        "cert_date": None,
        "cert_mail": "property_address",
        "cert_phone": "phone",
        "note": None,
        "notified": None,
        "code_violation": None,
        "date_offered": None,
        "date_note": None,
        "date_increase": None,
        "lease": None,
        "lease_renewal": None,
        "no_rent_due": None,
        "rent_increase": None,
        "rent_offered": None,
        "rent_paid": None,
        "rent_accepted": None,
        "status": None,
        "additional_info": None,
        "additional_reasons": None,
    }
    for cert_key, source_key in cert_synthesis.items():
        if cert_key not in _all_data:
            if source_key and source_key in _all_data:
                _all_data[cert_key] = _all_data[source_key]
            elif source_key is None:
                _all_data[cert_key] = ""
    
    # Set certificate dates to today
    today_str = date.today().strftime("%m/%d/%Y")
    for k in ["cert_date", "cert_date_signed"]:
        if k not in _all_data or not _all_data.get(k):
            _all_data[k] = today_str
    
    # Map each field_mapping key to a value from our data
    for map_key, pdf_field in mapping.items():
        if map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
    
    # Also apply fee_waiver_mapping if present (different field names for fee waivers)
    fw_mapping = config.get("fee_waiver_mapping", {})
    financial = data.get("financial_info", {})
    for map_key, pdf_field in fw_mapping.items():
        # Handle financial boolean fields as checkboxes
        if map_key.startswith("receives_") or map_key in ("income_below_threshold", "unable_to_pay_fees"):
            val = _get_financial_value(map_key, data)
            if val:
                values[pdf_field] = "Yes"
        elif map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
        else:
            val = _get_financial_value(map_key, data)
            if val:
                values[pdf_field] = str(val)
    
    # Date
    if "date" in mapping:
        values[mapping["date"]] = date.today().strftime("%m/%d/%Y")
    
    # Month/day/year handling
    today = date.today()
    if "month" in mapping:
        values[mapping["month"]] = str(today.month)
    if "day" in mapping:
        values[mapping["day"]] = str(today.day)
    if "year" in mapping:
        values[mapping["year"]] = str(today.year)
    
    # Handle defense checkboxes
    defense_opts = config.get("defense_options", [])
    
    # Defense key aliases — maps chatbot's standard keys to state-specific keys used in configs
    DEFENSE_ALIASES = {
        "def_repairs": ["def_repairs", "def_conditions", "def_failed_repair", "def_repair", "def_failed_maintain", "def_habitability"],
        "def_amount": ["def_amount", "def_amount_wrong", "def_disagree_amount", "def_no_rent_due", "def_not_owed", "def_dispute_amount"],
        "def_attempted_pay": ["def_attempted_pay", "def_offered_pay", "def_offered_refused", "def_tried_to_pay", "def_refused_payment", "def_refused_rent"],
        "def_paid": ["def_paid", "def_rent_paid", "def_rent_paid_full"],
        "def_waived": ["def_waived", "def_waiver"],
        "def_retaliation": ["def_retaliation"],
        "def_fair_housing": ["def_fair_housing", "def_discrimination"],
        "def_accepted_rent": ["def_accepted_rent", "def_accepted_late"],
        "def_corrected": ["def_corrected", "def_cured", "def_did_repairs", "def_moved_out"],
        "def_not_owner": ["def_not_owner", "def_landlord_not_entitled", "def_ownership"],
        "def_bad_notice": ["def_bad_notice", "def_no_notice", "def_invalid", "def_improper_notice"],
        "def_other": ["def_other", "def_other2", "def_other_defenses", "def_admit_all", "def_admit_partial", "def_deny_all", "def_contest", "def_jury_trial", "def_no_breach", "def_lease_violation", "def_justifiable"],
    }
    
    for opt in defense_opts:
        def_key = opt.get("key", "")
        field_name = opt.get("field", "")
        if def_key and field_name:
            # Check if any of our defense data matches this config key (or an alias)
            found_checked = False
            for standard_key, aliases in DEFENSE_ALIASES.items():
                if def_key in aliases:
                    def_data = defenses.get(standard_key, {})
                    checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
                    if checked:
                        values[field_name] = "Yes"
                        found_checked = True
                    break
            # Also check direct match (for keys not in alias list)
            if not found_checked:
                def_data = defenses.get(def_key, {})
                checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
                if checked:
                    values[field_name] = "Yes"
    
    # Static values: fixed text that doesn't come from user data
    # Used for fields like CA's "In Pro Per" attorney firm notation
    static_values = config.get("static_values", {})
    for pdf_field, static_text in static_values.items():
        values[pdf_field] = static_text

    # Smart auto-fill for common field names not in explicit mapping
    # Uses word-boundary matching to avoid false positives:
    #   "address" matches "AddressName2" but NOT "CourtAddress"
    #   "date" matches "Date3" but NOT "TrialDate" or "BOPDueDate"
    auto_fill_rules = [
        ("defendant", p.get("full_name", "")),
        ("plaintiff", l.get("landlord_name", "")),
        ("tenant", p.get("full_name", "")),
        ("landlord", l.get("landlord_name", "")),
        ("party1", l.get("landlord_name", "")),
        ("party2", p.get("full_name", "")),
        ("applicant", p.get("full_name", "")),
        ("case number", c.get("case_number", "")),
        ("case no", c.get("case_number", "")),
        ("file number", c.get("case_number", "")),
        ("docket", c.get("case_number", "")),
        ("phone", p.get("phone", "")),
        ("telephone", p.get("phone", "")),
        ("email", p.get("email", "")),
        ("county", p.get("county", "")),
        ("property", p.get("property_address", "")),
        ("street", p.get("property_address", "")),
        ("city or town", p.get("property_city", "")),
        ("signature", "/s/"),
        ("signed", today.strftime("%m/%d/%Y")),
    ]
    # Word-boundary-only rules: match "Date" or "Date3" but not "TrialDate" or "BOPDueDate"
    # Also handles camelCase like "ResidenceAddress" → "address"
    import re
    word_boundary_rules = [
        (re.compile(r'(?<![a-zA-Z])address|(?<=[a-z])Address', re.IGNORECASE), p.get("property_address", "")),
        (re.compile(r'(?<![a-zA-Z])date(?![a-zA-Z])|(?<=[a-z])Date$', re.IGNORECASE), today.strftime("%m/%d/%Y")),
        (re.compile(r'(?<![a-zA-Z])court(?![a-zA-Z])', re.IGNORECASE), c.get("court_name", "")),
        (re.compile(r'(?<![a-zA-Z])city', re.IGNORECASE), p.get("property_city", "")),
    ]
    # Field names that should NOT receive auto-fill from substring rules
    auto_fill_skip = re.compile(r'(court|trial|bop|file|attorney|judge|jury).*(address|date)', re.IGNORECASE)
    
    # Apply to each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        for widget in page.widgets():
            field_name = widget.field_name
            
            # 1. Check explicit mapping first
            if field_name in values:
                widget.field_value = values[field_name]
                widget.update()
                continue
            
            # 1b. UNIVERSAL DEFAULTS: checkboxes that should always be set for pro se tenants
            fn_lower = field_name.lower()
            if 'generally denies' in fn_lower or 'general denial' in fn_lower:
                widget.field_value = "Yes"
                widget.update()
                continue
            
            # 1c. Try partial name matching for long XFA widget names
            # e.g., "form1[0].FRONT[0].CERTNAME[0]" should match values["CERTNAME[0]"]
            parts = field_name.rsplit('.', 1)
            if len(parts) == 2:
                short_name = parts[1]
                if short_name in values:
                    widget.field_value = values[short_name]
                    widget.update()
                    continue
            
            # 1d. Skip auto-fill for fields that have any explicit mapping
            if field_name in mapping.values() or field_name in fw_mapping.values():
                continue
            
            # 2. Try auto-fill rules on field name (substring match)
            if not field_name:
                continue
            # Skip fields that shouldn't get auto-filled (court/trial/attorney address/date)
            if auto_fill_skip.search(field_name):
                continue
            fn_lower = field_name.lower()
            matched = False
            for keyword, value in auto_fill_rules:
                if value and keyword in fn_lower:
                    widget.field_value = str(value)
                    widget.update()
                    matched = True
                    break
            if matched:
                continue
            # 3. Try word-boundary rules (exact word match, not substring)
            for pattern, value in word_boundary_rules:
                if value and pattern.search(field_name):
                    widget.field_value = str(value)
                    widget.update()
                    break


def _fill_via_overlay(doc: fitz.Document, data: dict, config: dict, form_key: str = "answer_form"):
    """Overlay text on scanned/non-fillable PDFs using coordinate positions.
    
    For fee waivers, uses fee_waiver_overlay if available, otherwise falls back
    to overlay_positions. Falls back to stamping info at the top of the form.
    """
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    
    # For fee waivers, use fee_waiver_overlay ONLY — don't fall back to answer form positions
    if form_key == "fee_waiver_form":
        positions = dict(config.get("fee_waiver_overlay", {}))
    else:
        positions = dict(config.get("overlay_positions", {}))
        positions.update(config.get("fee_waiver_overlay", {}))
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # For fee waiver forms, ALWAYS stamp financial info on first page
        if form_key == "fee_waiver_form" and page_num == 0:
            fin = data.get("financial_info")
            if fin:
                fin_lines = []
                income = fin.get("monthly_gross_income") or fin.get("employment_income")
                if income: fin_lines.append(f"Monthly Income: ${float(income):,.2f}")
                adults = fin.get("household_adults")
                children = fin.get("household_children")
                if adults or children:
                    hh = f"Household: {adults or 0} adult(s)"
                    if children: hh += f", {children} child(ren)"
                    fin_lines.append(hh)
                benefits = []
                if fin.get("receives_snap"): benefits.append("SNAP")
                if fin.get("receives_medicaid"): benefits.append("Medicaid")
                if fin.get("receives_ssi"): benefits.append("SSI")
                if fin.get("receives_tanf"): benefits.append("TANF")
                if benefits: fin_lines.append(f"Benefits: {', '.join(benefits)}")
                vehicle = fin.get("vehicle_make_model")
                vehicle_val = fin.get("vehicle_value")
                if vehicle:
                    vtext = f"Vehicle: {vehicle}"
                    if vehicle_val: vtext += f" (${float(vehicle_val):,.2f})"
                    fin_lines.append(vtext)
                checking = fin.get("checking_balance")
                savings = fin.get("savings_balance")
                cash = fin.get("cash_on_hand")
                if checking or savings or cash:
                    total = (checking or 0) + (savings or 0) + (cash or 0)
                    fin_lines.append(f"Bank/Cash: ${float(total):,.2f}")
                if fin_lines:
                    fin_text = "\n".join(fin_lines)
                    fin_rect = fitz.Rect(50, 250, 550, 400)
                    page.insert_textbox(fin_rect, fin_text, fontname="helv", fontsize=9, color=(0, 0, 0))
        
        if positions:
            # Use precise coordinates for this state
            for key, pos in positions.items():
                if pos.get("page", 1) - 1 != page_num:
                    continue
                value = _get_field_value(key, data)
                if not value:
                    continue
                
                # Check if this is a defense checkbox (small overlay rect)
                is_checkbox = key.startswith("def_") and pos.get("h", 20) <= 20
                
                if is_checkbox:
                    # Draw a proper checkmark (✓) using lines
                    cx = pos["x"]
                    cy = pos["y"]
                    s = pos.get("h", 14)  # use height as scale
                    # Draw the checkmark as two lines: \ and /
                    page.draw_line(
                        fitz.Point(cx, cy + s * 0.5),
                        fitz.Point(cx + s * 0.35, cy + s * 0.9),
                        color=(0, 0, 0), width=1.5
                    )
                    page.draw_line(
                        fitz.Point(cx + s * 0.35, cy + s * 0.9),
                        fitz.Point(cx + s * 0.8, cy + s * 0.15),
                        color=(0, 0, 0), width=1.5
                    )
                else:
                    rect = fitz.Rect(pos["x"], pos["y"], pos["x"] + pos.get("w", 200), pos["y"] + pos.get("h", 20))
                    page.insert_textbox(
                        rect, str(value),
                        fontname="helv",
                        fontsize=pos.get("size", 10),
                        color=(0, 0, 0),
                    )
        else:
            # No position config — stamp info block at top of first page
            if page_num == 0:
                text_lines = []
                if p.get("full_name"): text_lines.append(f"Defendant: {p['full_name']}")
                if l.get("landlord_name"): text_lines.append(f"Plaintiff: {l['landlord_name']}")
                if c.get("case_number"): text_lines.append(f"Case No: {c['case_number']}")
                if p.get("phone"): text_lines.append(f"Phone: {p['phone']}")
                text_lines.append(f"Date: {date.today().strftime('%m/%d/%Y')}")
                
                # Include financial summary when financial_info is present (fee waivers)
                fin = data.get("financial_info")
                if fin:
                    text_lines.append("")
                    income = fin.get("monthly_gross_income") or fin.get("employment_income")
                    if income: text_lines.append(f"Monthly Income: ${float(income):,.2f}")
                    adults = fin.get("household_adults")
                    children = fin.get("household_children")
                    if adults or children:
                        hh = f"Household: {adults or 0} adult(s)"
                        if children: hh += f", {children} child(ren)"
                        text_lines.append(hh)
                    benefits = []
                    if fin.get("receives_snap"): benefits.append("SNAP")
                    if fin.get("receives_medicaid"): benefits.append("Medicaid")
                    if fin.get("receives_ssi"): benefits.append("SSI")
                    if fin.get("receives_tanf"): benefits.append("TANF")
                    if benefits: text_lines.append(f"Benefits: {', '.join(benefits)}")
                    vehicle = fin.get("vehicle_make_model")
                    vehicle_val = fin.get("vehicle_value")
                    if vehicle:
                        vtext = f"Vehicle: {vehicle}"
                        if vehicle_val: vtext += f" (${float(vehicle_val):,.2f})"
                        text_lines.append(vtext)
                    checking = fin.get("checking_balance")
                    savings = fin.get("savings_balance")
                    cash = fin.get("cash_on_hand")
                    if checking or savings or cash:
                        total = (checking or 0) + (savings or 0) + (cash or 0)
                        text_lines.append(f"Bank/Cash: ${float(total):,.2f}")
                
                text = "\n".join(text_lines)
                rect = fitz.Rect(50, 50, 550, 300)
                page.insert_textbox(rect, text, fontname="helv", fontsize=10, color=(0, 0, 0))


def _get_field_value(key: str, data: dict) -> Optional[str]:
    """Get a value from the nested data dict by key path.
    
    Handles regular data fields, defense checkbox overlay keys, and narrative text.
    When key starts with 'def_', returns 'X' if the defense is checked (triggers checkmark).
    When key is 'defense_narrative', returns formatted defense explanation text.
    """
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    
    mapper = {
        "full_name": p.get("full_name"),
        "phone": p.get("phone"),
        "email": p.get("email"),
        "address": p.get("property_address"),
        "city": p.get("property_city"),
        "zip": p.get("property_zip"),
        "county": p.get("county"),
        "landlord_name": l.get("landlord_name"),
        "landlord_address": l.get("landlord_address"),
        "landlord_phone": l.get("landlord_phone"),
        "landlord_email": l.get("landlord_email"),
        "case_number": c.get("case_number"),
        "court_name": c.get("court_name"),
        "monthly_rent": str(c.get("monthly_rent", "")),
        "amount_demanded": str(c.get("notice_amount_demanded", "")),
    }
    
    # Handle defense narrative text generation
    if key == "defense_narrative":
        return _build_defense_narrative(defenses)
    
    # Handle financial summary for overlay fee waiver forms
    if key == "financial_summary":
        return _build_financial_summary(data.get("financial_info", {}))
    
    # Handle defense checkbox overlay keys
    if key.startswith("def_"):
        # Map aliases for state-specific defense keys
        DEFENSE_ALIASES = {
            "def_not_owner2": "def_not_owner",
            "def_victim_status": "def_other",
            "def_rental_assistance": "def_other",
            "def_dismiss": "def_other",
            "def_counterclaim": "def_other",
            "def_failure_mitigate": "def_other",
            "def_wrong_reason": "def_bad_notice",
            "def_moved_out": "def_other",
            "def_foreclosure": "def_other",
            "def_pre_termination": "def_other",
            "def_other2": "def_other",
        }
        lookup_key = DEFENSE_ALIASES.get(key, key)
        def_data = defenses.get(lookup_key, {})
        checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
        if checked:
            return "X"  # triggers overlay to draw checkmark lines
        return None
    
    return mapper.get(key)


def _get_financial_value(key: str, data: dict) -> Optional[str]:
    """Get a value from the FinancialInfo section for fee waiver forms.
    
    Returns formatted string for text fields, or "Yes" for boolean checkboxes.
    """
    financial = data.get("financial_info", {})
    if not financial:
        return None
    
    # Boolean checkbox fields
    bool_fields = ["receives_public_benefits", "receives_snap", "receives_ssi", "receives_medicaid",
                   "receives_tanf", "receives_section8", "receives_public_housing",
                   "receives_county_assistance", "receives_energy_assistance",
                   "receives_veterans_benefits", "receives_child_care_assistance",
                   "income_below_threshold", "unable_to_pay_fees", "owns_real_estate",
                   "has_requested_fee_waiver_before"]
    if key in bool_fields:
        val = financial.get(key, False)
        return "Yes" if val else None
    
    # Numeric fields — format as dollar amounts
    dollar_fields = ["monthly_gross_income", "monthly_net_income", "employment_income",
                     "self_employment_income", "social_security_income", "ssi_income",
                     "unemployment_income", "pension_income", "disability_income",
                     "veterans_benefits", "child_support_income", "alimony_income",
                     "other_income", "rent_or_mortgage", "utilities_expense",
                     "food_expense", "transportation_expense", "medical_expense",
                     "child_care_expense", "debt_payments", "other_expenses",
                     "total_monthly_expenses", "cash_on_hand", "checking_balance",
                     "savings_balance", "vehicle_value", "vehicle_loan_owed",
                     "real_estate_value", "real_estate_loan_owed", "other_assets_value"]
    if key in dollar_fields:
        val = financial.get(key)
        if val is not None and val != 0:
            return f"${float(val):,.2f}"
        return None
    
    # Text fields
    text_fields = ["vehicle_make_model", "other_income_description", "other_assets_description",
                   "previous_fee_waiver_case"]
    if key in text_fields:
        val = financial.get(key)
        return str(val) if val else None
    
    # Household numbers
    if key in ["household_adults", "household_children", "total_dependents"]:
        val = financial.get(key)
        return str(val) if val is not None else None
    
    return None


def _build_financial_summary(financial: dict) -> str:
    """Build a formatted summary of financial data for overlay fee waiver forms."""
    if not financial:
        return ""
    
    lines = []
    
    # Income
    income = financial.get('monthly_gross_income')
    if income:
        lines.append(f"Monthly Gross Income: ${float(income):,.2f}")
    emp = financial.get('employment_income')
    if emp:
        lines.append(f"Employment: ${float(emp):,.2f}")
    
    # Household
    adults = financial.get('household_adults', 1)
    children = financial.get('household_children', 0)
    lines.append(f"Household: {adults} adult(s), {children} child(ren)")
    
    # Benefits
    benefits = []
    if financial.get('receives_snap'): benefits.append('SNAP')
    if financial.get('receives_ssi'): benefits.append('SSI')
    if financial.get('receives_medicaid'): benefits.append('Medicaid')
    if financial.get('receives_tanf'): benefits.append('TANF')
    if financial.get('receives_section8'): benefits.append('Section 8')
    if benefits:
        lines.append(f"Public Benefits: {', '.join(benefits)}")
    
    # Expenses
    rent = financial.get('rent_or_mortgage')
    if rent:
        lines.append(f"Rent/Mortgage: ${float(rent):,.2f}")
    total_exp = financial.get('total_monthly_expenses')
    if total_exp:
        lines.append(f"Total Monthly Expenses: ${float(total_exp):,.2f}")
    
    # Assets
    cash_val = financial.get('cash_on_hand')
    if cash_val:
        lines.append(f"Cash on Hand: ${float(cash_val):,.2f}")
    checking = financial.get('checking_balance')
    if checking:
        lines.append(f"Checking: ${float(checking):,.2f}")
    savings = financial.get('savings_balance')
    if savings:
        lines.append(f"Savings: ${float(savings):,.2f}")
    vehicle = financial.get('vehicle_make_model')
    if vehicle:
        vehicle_val = financial.get('vehicle_value')
        lines.append(f"Vehicle: {vehicle} (${float(vehicle_val):,.2f})" if vehicle_val else f"Vehicle: {vehicle}")
    
    return '\n'.join(lines)


def _build_defense_narrative(defenses: dict) -> str:
    """Build a formatted paragraph of defense explanations from checked defenses.
    Used for narrative court forms (AR, NM, TN) that have blank text areas.
    """
    DEFENSE_LABELS = {
        "def_repairs": "The landlord failed to make necessary repairs to the property despite being notified. "
                       "This includes [describe specific repair issues].",
        "def_did_repairs": "I made repairs to the property that the landlord should have made, "
                          "and I am entitled to deduct these costs from rent.",
        "def_amount": "I dispute the amount of rent the landlord claims I owe. "
                      "I believe the correct amount is [state amount and reason].",
        "def_paid": "I have already paid the rent that the landlord claims is owed. "
                    "I have proof of payment including [describe receipts, bank statements, etc.].",
        "def_attempted_pay": "I tried to pay my rent but the landlord refused to accept payment. "
                           "I made a good faith effort to pay on [date(s)].",
        "def_retaliation": "The landlord is evicting me in retaliation for exercising my legal rights. "
                         "Specifically, after I [complained to code enforcement / requested repairs / etc.], "
                         "the landlord filed this eviction.",
        "def_discrimination": "The eviction is discriminatory and violates fair housing laws. "
                             "I believe I am being treated differently because of [protected characteristic].",
        "def_bad_notice": "The landlord did not provide proper legal notice before filing this eviction. "
                         "The notice was [defective / not served properly / missing required information].",
        "def_landlord_breach": "The landlord breached the rental agreement by [describe violation].",
        "def_not_owner": "The person or company suing me is not the actual owner of the property.",
        "def_waived": "The landlord waived the right to evict by [accepting rent after notice / telling me I could stay / etc.].",
        "def_accepted_rent": "The landlord accepted my rent payment after sending the eviction notice, "
                            "which cancels the eviction.",
        "def_corrected": "I corrected the lease violation that the landlord complained about before the deadline.",
        "def_other": "I have additional reasons why I should not be evicted. [Describe here].",
        "def_contest": "This court does not have proper jurisdiction over this case.",
        "def_dismiss": "The complaint should be dismissed because [state reason].",
    }
    
    checked = []
    for key, label in DEFENSE_LABELS.items():
        d = defenses.get(key, {})
        if isinstance(d, dict) and d.get("checked"):
            explanation = d.get("explanation", "")
            text = label
            if explanation:
                # Replace placeholder with actual explanation
                text = text.replace("[describe specific repair issues]", explanation)
                text = text.replace("[state amount and reason]", explanation)
                text = text.replace("[describe receipts, bank statements, etc.]", explanation)
                text = text.replace("[date(s)]", explanation)
                text = text.replace("[complained to code enforcement / requested repairs / etc.]", explanation)
                text = text.replace("[protected characteristic]", explanation)
                text = text.replace("[defective / not served properly / missing required information]", explanation)
                text = text.replace("[describe violation]", explanation)
                text = text.replace("[accepting rent after notice / telling me I could stay / etc.]", explanation)
                text = text.replace("[Describe here]", explanation)
                text = text.replace("[state reason]", explanation)
            checked.append(text)
    
    if not checked:
        return "The defendant requests that the court deny the eviction and allow the defendant to remain in possession of the premises."
    
    # Number the defenses
    lines = []
    for i, def_text in enumerate(checked, 1):
        lines.append(f"{i}. {def_text}")
    
    return "\n\n".join(lines)
