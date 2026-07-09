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
    """Fill a state's eviction answer form — handles fillable AND scanned PDFs.
    
    First attempts field-level filling. Falls back to coordinate-based overlay.
    
    Args:
        data: Case data dict with personal_info, landlord_info, case_details, defenses
        state: State code (VA, SC, GA, TX, etc.)
        output_path: Where to save the filled PDF
    
    Returns:
        True if successful
    """
    state_code = state.upper()
    config = get_state_config(state_code)
    if not config:
        logger.warning(f"No state config for {state_code}")
        return False

    form_filename = config.get("answer_form")
    if not form_filename:
        logger.warning(f"No answer form for {state_code}")
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
    has_fields = len(doc.xref_get_keys(doc.pdf_catalog) or []) > 0  # simplistic check
    # Better: try to get form fields
    try:
        fields_count = len(doc.load_page(0).widgets())
        has_fields = fields_count > 0
    except:
        has_fields = False

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
    """Fill a PDF's form fields using widget/field mapping."""
    mapping = config.get("field_mapping", {})
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    
    # Build field values
    values = {}
    
    # Map generic fields to PDF fields
    generic_to_field = {
        "full_name": p.get("full_name", ""),
        "landlord_name": l.get("landlord_name", ""),
        "case_number": c.get("case_number", ""),
        "phone": p.get("phone", ""),
        "email": p.get("email", ""),
        "address": p.get("property_address", ""),
        "county": p.get("county", ""),
        "property_address": p.get("property_address", ""),
        "landlord_address": l.get("landlord_address", ""),
        "landlord_phone": l.get("landlord_phone", ""),
        "landlord_email": l.get("landlord_email", ""),
    }
    
    for generic_key, value in generic_to_field.items():
        if value and generic_key in mapping:
            values[mapping[generic_key]] = str(value)
    
    # Date
    if "date" in mapping:
        values[mapping["date"]] = date.today().strftime("%m/%d/%Y")
    
    # Handle defense checkboxes
    defenses = data.get("defenses", {})
    defense_opts = config.get("defense_options", [])
    for opt in defense_opts:
        def_key = opt.get("key", "")
        field_name = opt.get("field", "")
        if def_key and field_name:
            def_data = defenses.get(def_key, {})
            checked = def_data.get("checked", False) if isinstance(def_data, dict) else False
            if checked:
                values[field_name] = "Yes"
    
    # Apply to each page
    for page_num in range(len(doc)):
        page = doc[page_num]
        widgets = page.widgets()
        for widget in widgets:
            field_name = widget.field_name
            if field_name in values:
                widget.field_value = values[field_name]
                widget.update()


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
