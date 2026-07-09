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

    if has_fields:
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
    
    values = {}
    
    # Map each field_mapping key to a value from our data
    for map_key, pdf_field in mapping.items():
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
    
    # Smart auto-fill for common field names not in explicit mapping
    auto_fill_rules = [
        ("defendant", p.get("full_name", "")),
        ("plaintiff", l.get("landlord_name", "")),
        ("tenant", p.get("full_name", "")),
        ("landlord", l.get("landlord_name", "")),
        ("case number", c.get("case_number", "")),
        ("case no", c.get("case_number", "")),
        ("file number", c.get("case_number", "")),
        ("phone", p.get("phone", "")),
        ("telephone", p.get("phone", "")),
        ("email", p.get("email", "")),
        ("address", p.get("property_address", "")),
        ("county", p.get("county", "")),
        ("property", p.get("property_address", "")),
        ("date", today.strftime("%m/%d/%Y")),
        ("signature", "/s/"),
        ("signed", today.strftime("%m/%d/%Y")),
    ]
    
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
            
            # 2. Try auto-fill rules on field name
            if not field_name:
                continue
            fn_lower = field_name.lower()
            for keyword, value in auto_fill_rules:
                if value and keyword in fn_lower:
                    widget.field_value = str(value)
                    widget.update()
                    break


def _fill_via_overlay(doc: fitz.Document, data: dict, config: dict):
    """Overlay text on scanned/non-fillable PDFs using coordinate positions.
    
    Uses position_config from state config to place text at correct locations.
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
                if value:
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
    """Get a value from the nested data dict by key path."""
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    
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
    return mapper.get(key)
