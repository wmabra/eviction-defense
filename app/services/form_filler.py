"""Official court form filler — populates fillable PDFs with case data."""
import os
import logging
from io import BytesIO
from datetime import date
from PyPDF2 import PdfReader, PdfWriter

from app.services.state_configs import get_state_config

logger = logging.getLogger(__name__)

# Path to blank court forms
FORMS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")

# County-specific form files
COUNTY_FORMS = {
    "Miami-Dade": "answer_form_704.pdf",
}

STATE_FORMS = {
    "AR": "ar_eviction_answer.pdf",
    "AZ": "az_eviction_answer.pdf",
    "CA": "ca_ud105.pdf",
    "CO": "co_eviction_answer.pdf",
    "CT": "ct_eviction_answer.pdf",
    "FL": "answer_form_917.pdf",
    "GA": "ga_eviction_answer.pdf",
    "IL": "il_eviction_answer.pdf",
    "LA": "la_eviction_answer.pdf",
    "MI": "mi_eviction_answer.pdf",
    "MN": "mn_eviction_answer.pdf",
    "MS": "ms_eviction_answer.pdf",
    "NC": "nc_eviction_answer.pdf",
    "NM": "nm_eviction_answer.pdf",
    "NV": "nv_answer_nonpayment.pdf",
    "OR": "or_eviction_answer.pdf",
    "RI": "ri_eviction_answer.pdf",
    "SC": "sc_eviction_answer.pdf",
    "TN": "tn_eviction_answer.pdf",
    "TX": "tx_eviction_answer.pdf",
    "VA": "va_eviction_answer.pdf",
}

FEE_WAIVER_FORMS = {
    "AR": "ar_fee_waiver.pdf",
    "AZ": "az_fee_waiver.pdf",
    "CA": "ca_fee_waiver.pdf",
    "CO": "co_fee_waiver.pdf",
    "CT": "ct_fee_waiver.pdf",
    "FL": "fl_fee_waiver.pdf",
    "GA": "ga_fee_waiver.pdf",
    "IL": "il_fee_waiver.pdf",
    "LA": "la_fee_waiver.pdf",
    "MI": "mi_fee_waiver.pdf",
    "MN": "mn_fee_waiver.pdf",
    "MS": "ms_fee_waiver.pdf",
    "NC": "nc_fee_waiver.pdf",
    "NM": "nm_fee_waiver.pdf",
    "NV": "nv_fee_waiver.pdf",
    "OR": "or_fee_waiver.pdf",
    "RI": "ri_fee_waiver.pdf",
    "SC": "sc_fee_waiver.pdf",
    "TN": "tn_fee_waiver.pdf",
    "TX": "tx_fee_waiver.pdf",
    "VA": "va_fee_waiver.pdf",
}




def fill_answer_form(data: dict, state: str, output_path: str) -> bool:
    """Fill the official court eviction answer form using state-specific config.
    
    Args:
        data: Case data dict
        state: State code (FL, CA, IL, VA, etc.)
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
        logger.warning(f"No answer form configured for {state_code}")
        return False
    
    if not config.get("has_fillable_fields", False):
        logger.warning(f"{state_code} form is not fillable PDF — use overlay or PDF generation instead")
        return False
    
    form_path = os.path.join(FORMS_DIR, form_filename)
    if not os.path.exists(form_path):
        logger.error(f"Form not found: {form_path}")
        return False
    
    reader = PdfReader(form_path)
    writer = PdfWriter()
    writer.append(reader)
    
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    
    mapping = config.get("field_mapping", {})
    updates = {}
    
    # Map generic fields to state-specific PDF fields
    if "full_name" in mapping and p.get("full_name"):
        updates[mapping["full_name"]] = p["full_name"]
    
    if "landlord_name" in mapping and l.get("landlord_name"):
        updates[mapping["landlord_name"]] = l["landlord_name"]
    
    if "case_number" in mapping and c.get("case_number"):
        updates[mapping["case_number"]] = c["case_number"]
    
    if "phone" in mapping and p.get("phone"):
        updates[mapping["phone"]] = p["phone"]
    
    if "email" in mapping and p.get("email"):
        updates[mapping["email"]] = p["email"]
    
    if "address" in mapping and p.get("property_address"):
        updates[mapping["address"]] = p["property_address"]
    
    if "county" in mapping and p.get("county"):
        updates[mapping["county"]] = p["county"]
    
    if "date" in mapping:
        updates[mapping["date"]] = date.today().strftime("%m/%d/%Y")
    
    # Handle defense checkboxes
    defense_options = config.get("defense_options", [])
    for opt in defense_options:
        def_key = opt.get("key", "")
        field_name = opt.get("field", "")
        if def_key and field_name:
            defense = defenses.get(def_key, {})
            checked = defense.get("checked", False) if isinstance(defense, dict) else False
            if checked:
                updates[field_name] = "/Yes" if state_code in ("SC",) else "1"
    
    # Apply all updates
    try:
        writer.update_page_form_field_values(writer.pages[0], updates)
    except Exception as e:
        logger.warning(f"Some fields couldn't be updated: {e}")
        try:
            fields = reader.get_fields()
            for key, value in updates.items():
                if key in fields:
                    writer.update_page_form_field_values(writer.pages[0], {key: value})
        except Exception:
            pass
    
    with open(output_path, "wb") as f:
        writer.write(f)
    
    logger.info(f"Filled {state_code} form saved to {output_path}")
    return True
    
    # Add explanations for checked defenses
    for def_key, defense in defenses.items():
        if isinstance(defense, dict) and defense.get("checked") and defense.get("explanation"):
            # Try to find corresponding explanation field
            exp_field = f"Explain {def_key}"
            if exp_field in reader.get_fields():
                updates[exp_field] = defense["explanation"]
    
    # Trial preference
    pref = data.get("preferences", {})
    if pref.get("trial_by") == "judge":
        updates["I want a judge to decide my case Click here if you want a trial by judge"] = "/Yes"
    elif pref.get("trial_by") == "jury":
        updates["I want a jury to decide my case Click here if you want a trial by jury"] = "/Yes"
    
    # Date
    from datetime import date
    updates["Date"] = date.today().strftime("%m/%d/%Y")
    
    # Apply all updates
    try:
        writer.update_page_form_field_values(writer.pages[0], updates)
    except Exception as e:
        logger.warning(f"Some fields couldn't be updated: {e}")
        # Try field-by-field
        fields = reader.get_fields()
        for key, value in updates.items():
            try:
                if key in fields:
                    writer.update_page_form_field_values(writer.pages[0], {key: value})
            except:
                pass
    
    # Write output
    with open(output_path, "wb") as f:
        writer.write(f)
    
    logger.info(f"Filled form saved to {output_path}")
    return True


def get_supported_counties() -> list[str]:
    """Return list of counties with official form templates."""
    return list(COUNTY_FORMS.keys())
