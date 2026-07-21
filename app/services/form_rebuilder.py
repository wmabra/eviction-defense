"""
Court Form Rebuilder — creates clean, fillable PDFs from official court forms.

Takes each state's official court form, renders it as a background image,
and places standardized AcroForm widgets at the exact overlay positions.
Result: identical to the official form but with clean, predictable field names.
"""

import os
import fitz
import logging

logger = logging.getLogger(__name__)

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")
REBUILT_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "rebuilt")

# Universal field names — same across all 20 states
STANDARD_FIELDS = {
    "defendant_name": {"label": "Defendant Name", "type": "text"},
    "plaintiff_name": {"label": "Plaintiff / Landlord Name", "type": "text"},
    "case_number": {"label": "Case Number", "type": "text"},
    "court_name": {"label": "Court Name", "type": "text"},
    "county": {"label": "County", "type": "text"},
    "property_address": {"label": "Property Address", "type": "text"},
    "phone": {"label": "Phone Number", "type": "text"},
    "email": {"label": "Email Address", "type": "text"},
    "date": {"label": "Date", "type": "text"},
    "printed_name": {"label": "Print Name", "type": "text"},
    "signature": {"label": "Signature", "type": "text"},
    "defense_repairs": {"label": "Defense: Repairs", "type": "checkbox"},
    "defense_amount": {"label": "Defense: Dispute Amount", "type": "checkbox"},
    "defense_attempted_pay": {"label": "Defense: Attempted to Pay", "type": "checkbox"},
    "defense_paid": {"label": "Defense: Already Paid", "type": "checkbox"},
    "defense_waived": {"label": "Defense: Notice Waived", "type": "checkbox"},
    "defense_retaliation": {"label": "Defense: Retaliation", "type": "checkbox"},
    "defense_discrimination": {"label": "Defense: Discrimination", "type": "checkbox"},
    "defense_accepted_rent": {"label": "Defense: Accepted Rent After Notice", "type": "checkbox"},
    "defense_corrected": {"label": "Defense: Already Corrected", "type": "checkbox"},
    "defense_not_owner": {"label": "Defense: Not the Owner", "type": "checkbox"},
    "defense_bad_notice": {"label": "Defense: Improper Notice", "type": "checkbox"},
    "defense_other": {"label": "Defense: Other", "type": "checkbox"},
    "defense_narrative": {"label": "Defense Explanation", "type": "text"},
    "financial_summary": {"label": "Financial Summary", "type": "text"},
    "rent_amount": {"label": "Monthly Rent", "type": "text"},
    "amount_claimed": {"label": "Amount Claimed", "type": "text"},
}


def rebuild_all_states():
    """Rebuild all 20 states' court forms with standardized fields."""
    from app.services.state_configs import STATE_CONFIGS
    
    os.makedirs(REBUILT_DIR, exist_ok=True)
    results = {}
    
    for state_code in sorted(STATE_CONFIGS.keys()):
        try:
            result = rebuild_state(state_code)
            results[state_code] = result
            print(f"  {state_code}: {result}")
        except Exception as e:
            results[state_code] = f"ERROR: {e}"
            print(f"  {state_code}: ERROR - {e}")
    
    passed = sum(1 for v in results.values() if "OK" in str(v))
    print(f"\nRebuilt: {passed}/20 states")
    return results


def rebuild_state(state_code: str):
    """Rebuild a single state's court form with standardized fields."""
    from app.services.state_configs import STATE_CONFIGS
    
    config = STATE_CONFIGS.get(state_code)
    if not config:
        return "No config found"
    
    form_filename = config.get("answer_form")
    if not form_filename:
        return "No form configured"
    
    source_path = os.path.join(TEMPLATES_DIR, form_filename)
    if not os.path.exists(source_path):
        return f"Source not found: {form_filename}"
    
    # Get overlay positions from config
    overlay_positions = config.get("overlay_positions", {})
    field_mapping = config.get("field_mapping", {})
    defense_options = config.get("defense_options", [])
    
    # Map our standard field names to the positions in the state config
    field_placements = _map_fields_to_positions(state_code, overlay_positions, field_mapping, defense_options)
    
    if not field_placements:
        return "No field positions — needs manual mapping"
    
    # Open source and create new document
    source = fitz.open(source_path)
    output_path = os.path.join(REBUILT_DIR, f"{state_code.lower()}_answer_rebuilt.pdf")
    output = fitz.open()
    
    for page_num in range(source.page_count):
        page = source[page_num]
        
        # Render page as high-res image
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        
        # Create new page with same dimensions
        new_page = output.new_page(width=page.rect.width, height=page.rect.height)
        
        # Insert the original form as background image
        new_page.insert_image(new_page.rect, stream=img_bytes)
        
        # Place standardized widgets for this page
        page_fields = [(name, pos) for name, pos in field_placements.items() 
                       if pos.get("page", 1) - 1 == page_num]
        
        for field_name, position in page_fields:
            _add_widget(new_page, field_name, position)
    
    output.save(output_path, deflate=True, garbage=4)
    output.close()
    source.close()
    
    return f"OK — {len(field_placements)} fields placed"


def _map_fields_to_positions(state_code, overlay_positions, field_mapping, defense_options):
    """Map standardized field names to their positions on the form."""
    placements = {}
    
    # 1. Data fields from overlay_positions
    overlay_key_map = {
        "full_name": "defendant_name",
        "landlord_name": "plaintiff_name",
        "case_number": "case_number",
        "court_name": "court_name",
        "county": "county",
        "address": "property_address",
        "phone": "phone",
        "email": "email",
        "date": "date",
        "printed_name": "printed_name",
        "signature": "signature",
        "defense_narrative": "defense_narrative",
        "financial_summary": "financial_summary",
        # Defense checkboxes
        "def_repairs": "defense_repairs",
        "def_did_repairs": "defense_corrected",
        "def_amount": "defense_amount",
        "def_attempted_pay": "defense_attempted_pay",
        "def_paid": "defense_paid",
        "def_waived": "defense_waived",
        "def_retaliation": "defense_retaliation",
        "def_fair_housing": "defense_discrimination",
        "def_discrimination": "defense_discrimination",
        "def_accepted_rent": "defense_accepted_rent",
        "def_corrected": "defense_corrected",
        "def_not_owner": "defense_not_owner",
        "def_not_owner2": "defense_not_owner",
        "def_bad_notice": "defense_bad_notice",
        "def_other": "defense_other",
        "def_other2": "defense_other",
        "def_dismiss": "defense_other",
        "def_contest": "defense_other",
        "def_conditions": "defense_repairs",
        "def_failed_repair": "defense_repairs",
        "def_no_rent_due": "defense_amount",
        "def_offered_pay": "defense_attempted_pay",
        "def_refused_payment": "defense_attempted_pay",
        "def_rent_paid": "defense_paid",
        "def_waiver": "defense_waived",
        "def_no_notice": "defense_bad_notice",
        "def_invalid": "defense_bad_notice",
        "def_admit_all": "defense_other",
        "def_admit_partial": "defense_other",
        "def_deny_all": "defense_other",
        "def_jury_trial": "defense_other",
        "def_lease_violation": "defense_other",
        "def_no_breach": "defense_other",
        "def_justifiable": "defense_other",
        "def_moved_out": "defense_corrected",
        "def_counterclaim": "defense_other",
        "def_failure_mitigate": "defense_other",
        "def_victim_status": "defense_other",
        "def_rental_assistance": "defense_other",
        "def_foreclosure": "defense_other",
        "def_pre_termination": "defense_other",
        "def_ownership": "defense_not_owner",
        "def_ownership_interest": "defense_not_owner",
        "def_landlord_not_entitled": "defense_not_owner",
    }
    
    for overlay_key, position in overlay_positions.items():
        std_key = overlay_key_map.get(overlay_key, overlay_key)
        placements[std_key] = position
    
    # 2. Defense checkboxes from defense_options
    defense_key_map = {
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
    
    for opt in defense_options:
        def_key = opt.get("key", "")
        std_key = defense_key_map.get(def_key)
        if not std_key:
            # Try alias matching
            for orig, std in defense_key_map.items():
                if def_key in [orig] or def_key.startswith(orig):
                    std_key = std
                    break
        if not std_key:
            std_key = "defense_other"
        
        # Defense options don't have positions — they use widget field names
        # For the rebuild, we need positions. Use overlay_positions if available.
        # Otherwise, mark as needing manual coordinate input.
        pos_key = f"def_{def_key}" if def_key in overlay_positions else None
        if pos_key and overlay_positions.get(pos_key):
            placements[std_key] = overlay_positions[pos_key]
    
    # 3. Also extract positions from the PDF's existing widgets (merge with overlay)
    widget_placements = _extract_positions_from_widgets(state_code)
    for k, v in widget_placements.items():
        if k not in placements:
            placements[k] = v
    
    return placements


def _extract_positions_from_widgets(state_code):
    """Extract ALL text field positions from an existing fillable PDF's widgets.
    Uses field_mapping from state config to map generic widget names to standard fields."""
    from app.services.state_configs import STATE_CONFIGS
    
    config = STATE_CONFIGS.get(state_code)
    if not config:
        return {}
    
    source_path = os.path.join(TEMPLATES_DIR, config["answer_form"])
    if not os.path.exists(source_path):
        return {}
    
    # Build reverse mapping: widget_name → standard_name from field_mapping
    field_mapping = config.get("field_mapping", {})
    reverse_map = {}
    std_key_map = {
        "full_name": "defendant_name",
        "landlord_name": "plaintiff_name",
        "case_number": "case_number",
        "court_name": "court_name",
        "county": "county",
        "address": "property_address",
        "phone": "phone",
        "email": "email",
        "date": "date",
        "printed_name": "printed_name",
    }
    for data_key, widget_name in field_mapping.items():
        std = std_key_map.get(data_key, data_key)
        reverse_map[widget_name.lower()] = std
    
    doc = fitz.open(source_path)
    placements = {}
    assigned = set()
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        for widget in page.widgets():
            fn = (widget.field_name or "").lower()
            rect = widget.rect
            pos = {
                "page": page_num + 1,
                "x": rect.x0,
                "y": rect.y0,
                "w": rect.width,
                "h": rect.height,
            }
            
            is_checkbox = rect.width < 30 and rect.height < 30
            
            # First: check reverse mapping (exact widget name match)
            if fn in reverse_map:
                std_name = reverse_map[fn]
                if std_name not in assigned:
                    placements[std_name] = pos
                    assigned.add(std_name)
                    continue
            
            if not is_checkbox and rect.width > 20:
                std_name = _map_widget_to_standard(fn, assigned)
                if std_name and std_name not in assigned:
                    placements[std_name] = pos
                    assigned.add(std_name)
            elif is_checkbox:
                std_name = _map_checkbox_to_standard(fn, assigned)
                if std_name and std_name not in assigned:
                    placements[std_name] = pos
                    assigned.add(std_name)
    
    doc.close()
    return placements


def _map_widget_to_standard(field_name, assigned):
    """Map a widget field name to a standard field name."""
    fn = field_name.lower()
    
    # Priority-ordered keyword matching (first match wins)
    patterns = [
        (["defendant", "tenant", "respondent"], "defendant_name"),
        (["plaintiff", "landlord", "petitioner", "lessor"], "plaintiff_name"),
        (["case number", "case no", "casenumber", "docket", "civil action file"], "case_number"),
        (["court name", "court", "magistrate"], "court_name"),
        (["county"], "county"),
        (["address", "street"], "property_address"),
        (["phone", "telephone", "telephone number"], "phone"),
        (["email", "e-mail"], "email"),
        (["date", "signed"], "date"),
        (["print", "signature", "sign"], "printed_name"),
        (["city", "zip"], "property_address"),  # secondary address fields
    ]
    
    for keywords, std_name in patterns:
        if std_name not in assigned:
            for kw in keywords:
                if kw in fn:
                    return std_name
    
    return None


def _map_checkbox_to_standard(field_name, assigned):
    """Map a checkbox widget to a standard defense field."""
    fn = field_name.lower()
    
    patterns = [
        (["repair", "condition", "habitability"], "defense_repairs"),
        (["amount", "owe", "rent due", "dispute amount", "not owe"], "defense_amount"),
        (["offer", "attempt", "refused", "tried to pay"], "defense_attempted_pay"),
        (["paid", "already paid", "rent paid"], "defense_paid"),
        (["waive", "cancel", "changed"], "defense_waived"),
        (["retaliat"], "defense_retaliation"),
        (["discriminat", "fair housing"], "defense_discrimination"),
        (["accept"], "defense_accepted_rent"),
        (["correct", "fix", "cured"], "defense_corrected"),
        (["owner", "not the owner"], "defense_not_owner"),
        (["notice", "improper", "legally"], "defense_bad_notice"),
        (["other", "additional"], "defense_other"),
    ]
    
    for keywords, std_name in patterns:
        if std_name not in assigned:
            for kw in keywords:
                if kw in fn:
                    return std_name
    
    return None


def _add_widget(page, field_name, position):
    """Add a standardized widget to a page. Defense fields are checkboxes."""
    x = position.get("x", 50)
    y = position.get("y", 50)
    w = position.get("w", 200)
    h = position.get("h", 20)
    
    # Defense fields are always checkboxes; everything else is text
    is_defense = field_name.startswith("defense_")
    
    if is_defense:
        widget = fitz.Widget()
        widget.field_name = field_name
        widget.field_type = fitz.PDF_WIDGET_TYPE_CHECKBOX
        widget.rect = fitz.Rect(x, y, x + 14, y + 14)
        widget.field_value = False
        page.add_widget(widget)
    else:
        widget = fitz.Widget()
        widget.field_name = field_name
        widget.field_type = fitz.PDF_WIDGET_TYPE_TEXT
        # Ensure text fields are wide enough
        if w < 50:
            w = 200
        if h < 14:
            h = 18
        rect = fitz.Rect(x, y, x + w, y + h)
        widget.rect = rect
        widget.field_value = ""
        widget.text_fontsize = position.get("size", 10)
        widget.text_font = "Helv"
        page.add_widget(widget)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
    rebuild_all_states()
