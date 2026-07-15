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

    form_path = os.path.join(FORMS_DIR, form_filename)
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
    
    if has_fields and has_overlay:
        # Hybrid: both fillable fields AND overlay positions (e.g., LA checkbox form + data overlay)
        _fill_via_widgets(doc, data, config)
        _fill_via_overlay(doc, data, config)
    elif has_fields:
        # Use fillable field approach
        _fill_via_widgets(doc, data, config)
    else:
        # Use coordinate overlay approach for scanned forms
        _fill_via_overlay(doc, data, config)

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
    
    # Build values from data using flexible key resolution
    _all_data = {}
    for section in [p, l, c]:
        for k, v in section.items():
            if v:
                _all_data[k] = str(v)
    
    # Add common aliases
    if "full_name" not in _all_data and "name" in _all_data:
        _all_data["full_name"] = _all_data["name"]
    if "landlord_name" not in _all_data and "landlord" in _all_data:
        _all_data["landlord_name"] = _all_data["landlord"]
    if "case_number" not in _all_data and "case" in _all_data:
        _all_data["case_number"] = _all_data["case"]
    if "address" not in _all_data and "property_address" in _all_data:
        _all_data["address"] = _all_data["property_address"]
    # Synthesize additional keys for forms that need them
    if "full_name" in _all_data:
        _all_data["submitted_name"] = _all_data["full_name"]
        _all_data["printed_name"] = _all_data["full_name"]
    if "address" in _all_data:
        _all_data["submitted_address2"] = _all_data["address"]
    
    # Auto-generate defense narrative for states with narrative text areas (TN, etc.)
    if "defense_narrative" in mapping:
        _all_data["defense_narrative"] = _build_defense_narrative(defenses)

    values = {}
    
    # Map each field_mapping key to a value from our data
    for map_key, pdf_field in mapping.items():
        if map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
    
    # Also apply fee_waiver_mapping if present (different field names for fee waivers)
    fw_mapping = config.get("fee_waiver_mapping", {})
    for map_key, pdf_field in fw_mapping.items():
        if map_key in _all_data:
            values[pdf_field] = str(_all_data[map_key])
    
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
    for opt in defense_opts:
        def_key = opt.get("key", "")
        field_name = opt.get("field", "")
        if def_key and field_name:
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


def _fill_via_overlay(doc: fitz.Document, data: dict, config: dict):
    """Overlay text on scanned/non-fillable PDFs using coordinate positions.
    
    Uses position_config from state config to place text at correct locations.
    For defense checkboxes, draws an actual checkmark symbol.
    Falls back to stamping info at the top of the form.
    """
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    
    positions = config.get("overlay_positions", {})
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
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
                
                text = "\n".join(text_lines)
                rect = fitz.Rect(50, 50, 550, 150)
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
