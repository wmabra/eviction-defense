"""Official court form filler — populates fillable PDFs with case data."""
import os
import logging
from io import BytesIO
from PyPDF2 import PdfReader, PdfWriter

logger = logging.getLogger(__name__)

# Path to blank court forms
FORMS_DIR = os.path.join(os.path.dirname(__file__), "..", "templates", "counties")

# County-specific form files
COUNTY_FORMS = {
    "Miami-Dade": "answer_form_704.pdf",
}

STATE_FORMS = {
    "CA": "ca_ud105.pdf",
    "IL": "il_eviction_answer.pdf",
    "TX": "tx_eviction_answer.pdf",
    "MI": "mi_eviction_answer.pdf",
    "NV": "nv_answer_nonpayment.pdf",
    "OR": "or_eviction_answer.pdf",
    "MN": "mn_eviction_answer.pdf",
    "FL": "answer_form_917.pdf",  # statewide FL fallback
}

FEE_WAIVER_FORMS = {
    "CA": "ca_fee_waiver.pdf",
    "MI": "mi_fee_waiver.pdf",
    "FL": "fl_fee_waiver.pdf",
}




def fill_answer_form(data: dict, state: str, output_path: str) -> bool:
    """Fill the official court eviction answer form.
    
    Args:
        data: Case data dict
        state: State code (FL, CA, IL, etc.) or county name (Miami-Dade)
        output_path: Where to save the filled PDF
    
    Returns:
        True if successful
    """
    # Check county-specific first, then state-level
    county = data.get("personal_info", {}).get("county", state)
    form_filename = COUNTY_FORMS.get(county) or STATE_FORMS.get(state.upper())
    
    if not form_filename:
        logger.warning(f"No form template for state={state}, county={county}")
        return False
    
    form_path = os.path.join(FORMS_DIR, form_filename)
    if not os.path.exists(form_path):
        logger.error(f"Form template not found: {form_path}")
        return False
    
    # Read the blank form
    reader = PdfReader(form_path)
    writer = PdfWriter()
    
    # Copy all pages and get fields
    writer.append(reader)
    
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    defenses = data.get("defenses", {})
    
    # Build the field updates dict
    updates = {}
    
    # Basic info
    updates["Defendant(s)"] = p.get("full_name", "")
    updates["Plaintiff(s)"] = l.get("landlord_name", "")
    updates["Case number"] = c.get("case_number", "")
    
    # Address info
    updates["Defendant(s) address"] = f"{p.get('property_address', '')}, {p.get('property_city', '')}, FL"
    
    # Phone/email
    updates["Defendants telephone number"] = p.get("phone", "")
    updates["Defendants email address"] = p.get("email", "")
    
    # Answer type — if they raised defenses, they deny
    has_defenses = any(
        isinstance(v, dict) and v.get("checked") 
        for k, v in defenses.items() 
        if k.startswith("def_")
    )
    
    if has_defenses:
        updates["Defendant generally denies each statement"] = "/Yes"
    else:
        updates["Defendant admits"] = "/Yes"
    
    # Check defense boxes (Miami-Dade form uses specific field names)
    defense_field_map = {
        "def_repairs": "The landlord did not make repairs and I withheld my rent after sending written notice to the landlord Click if this applies to you",
        "def_amount": "I do not owe the total amount of rent or ongoing amount of rent the landlord claims I owe Click if this applies to you",
        "def_attempted_pay": "I attemptedoffered to pay all the rent due before the notice to pay rent expired but the landlord did not accept the rent payment Click if this applies to you",
        "def_paid": "I paid the rent demanded by the landlord in the notice to pay rent Click if this applies to you",
        "def_waived": "The landlord waived, changed or canceled the notice that required me to move out Click if this applies to you",
        "def_retaliation": "The landlord filed the eviction in retaliation against me Click if this applies to you",
        "def_fair_housing": "The landlord filed the eviction in violation of the Federal Fair Housing Act andor the Florida Fair Housing Act Click if this applies to you",
        "def_accepted_rent": "The landlord accepted rent from me after sending me the notice to terminate Click if this applies to you",
        "def_corrected": "I already corrected the violations claimed by the landlord on the notice to terminate Click if this applies to you",
        "def_not_owner": "The landlord is not the owner of the property where I live Click if this applies to you",
        "def_bad_notice": "I did not receive the notice to terminate or the notice was legally incorrect Click if this applies to you",
        "def_other": "Other defenses set forth as follows Click if this applies to you",
    }
    
    for def_key, field_name in defense_field_map.items():
        defense = defenses.get(def_key, {})
        checked = defense.get("checked", False) if isinstance(defense, dict) else False
        if checked:
            updates[field_name] = "/Yes"
    
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
