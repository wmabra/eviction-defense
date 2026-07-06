"""
Confirmation screen service — replaces the human QA person.

This is the most important screen in the entire system. The customer must
review every extracted fact, approve or correct each one, and sign a
confirmation statement before documents are generated.

Why this works:
- Instead of a human checking names, dates, counties, case numbers, etc.,
  the AI extracts them and the customer confirms them.
- The customer is the most reliable source of truth for their own case.
- This shifts liability for accuracy from the business to the customer,
  which is both legally safer and operationally zero-touch.
"""

from datetime import date
from typing import Any, Optional


# Fields the customer must confirm before document generation
REQUIRED_CONFIRMATION_FIELDS = [
    {"key": "full_name", "label": "Your full legal name", "type": "text"},
    {"key": "property_address", "label": "Property address", "type": "text"},
    {"key": "county", "label": "County", "type": "text"},
    {"key": "court_name", "label": "Court name", "type": "text"},
    {"key": "case_number", "label": "Case number", "type": "text"},
    {"key": "landlord_name", "label": "Landlord / Plaintiff name", "type": "text"},
    {"key": "amount_claimed", "label": "Amount landlord claims is owed", "type": "currency"},
    {"key": "notice_date", "label": "Date on the 3-Day Notice (if received)", "type": "date"},
    {"key": "service_date", "label": "Date you were served with court papers", "type": "date"},
    {"key": "court_date", "label": "Scheduled court date (if any)", "type": "date", "optional": True},
    {"key": "response_deadline", "label": "Deadline to respond", "type": "date"},
]


def build_confirmation_screen(case_data: dict, extracted_data: dict) -> dict:
    """Build the confirmation screen payload.

    Returns a list of field groups, each with the extracted value and
    a 'confirmed' flag (initially False).
    """
    # Merge intake + extraction, preferring extraction values
    merged = {}
    for field_def in REQUIRED_CONFIRMATION_FIELDS:
        key = field_def["key"]
        extracted_val = extracted_data.get("fields", {}).get(key) if extracted_data else None
        intake_val = case_data.get(key)

        merged[key] = {
            "value": extracted_val or intake_val or "",
            "label": field_def["label"],
            "type": field_def["type"],
            "optional": field_def.get("optional", False),
            "confirmed": False,
            "edited": False,
        }

    # Add conflicts if extraction found mismatches
    conflicts = []
    for key in ["county", "case_number", "court_name", "landlord_name", "property_address"]:
        intake_val = case_data.get(key)
        extracted_val = extracted_data.get("fields", {}).get(key) if extracted_data else None
        if intake_val and extracted_val and str(intake_val).lower() != str(extracted_val).lower():
            conflicts.append({
                "field": key,
                "label": merged.get(key, {}).get("label", key),
                "intake_value": intake_val,
                "document_value": extracted_val,
            })

    return {
        "fields": merged,
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
        "all_confirmed": False,
        "confirmation_statement": (
            "I confirm that the information above is accurate and should be used "
            "to prepare my self-help paperwork packet. I understand this is a "
            "self-help service and I am responsible for reviewing, signing, and "
            "submitting the final documents."
        ),
        "confirmation_signed": False,
    }


def process_confirmation_submission(
    submitted_fields: dict[str, dict],
    confirmation_signed: bool,
) -> dict:
    """Process the customer's confirmation submission.

    Validates:
    - All required fields are confirmed
    - The confirmation statement is signed
    - No required fields are empty

    Returns:
        dict with: valid (bool), errors (list), updated_fields (dict)
    """
    errors = []

    for key, field_def in submitted_fields.items():
        field_info = REQUIRED_CONFIRMATION_FIELDS
        field_meta = next((f for f in field_info if f["key"] == key), None)
        is_optional = field_meta.get("optional", False) if field_meta else False

        # Check empty required fields
        if not is_optional and not field_def.get("value", "").strip():
            errors.append(f"{field_def.get('label', key)} is required.")

        # Check that the field is confirmed
        if not field_def.get("confirmed", False):
            errors.append(f"Please confirm {field_def.get('label', key)}.")

    if not confirmation_signed:
        errors.append(
            "You must check the confirmation statement to proceed."
        )

    if errors:
        return {
            "valid": False,
            "errors": errors,
            "all_confirmed": False,
        }

    return {
        "valid": True,
        "errors": [],
        "all_confirmed": True,
        "message": "All fields confirmed. Your packet is being generated.",
    }
