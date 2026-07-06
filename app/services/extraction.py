"""
AI extraction service — OCR + structured data extraction from uploaded documents.

This is the core intelligence layer. It takes uploaded eviction documents and
extracts structured fields (case number, dates, amounts, names) that the
customer then confirms. This replaces the need for a human QA person.

Flow:
1. Uploaded documents are OCR'd (Google Document AI)
2. Extracted text is sent to OpenAI with a structured output schema
3. Returned JSON maps to the case profile fields
4. Customer confirms or edits each field on the confirmation screen
"""

import json
import logging
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)

# The structured schema we ask the AI to extract
EXTRACTION_PROMPT = """
You are a legal document analysis AI. You analyze Florida eviction documents and
extract structured data from them. You only extract facts — you do NOT give legal
advice or interpretation.

Extract the following fields from the document text. If a field is not found,
leave it null. Be precise — exact names, dates, and numbers as they appear.

Fields to extract:
- customer_name: Full name of the tenant/defendant
- landlord_name: Full name of the landlord/plaintiff (LLC or individual)
- landlord_attorney: Name of landlord's attorney, if present
- property_address: Full address of the rental property
- county: County where the case is filed
- court_name: Name of the court
- case_number: Case number shown on the document
- amount_claimed: Dollar amount the landlord claims is owed
- notice_date: Date on the 3-day notice (if visible)
- service_date: Date the summons was served (if visible)
- court_date: Date of any scheduled hearing/court appearance
- response_deadline: Date by which a response must be filed
- document_type: Type of document (3-day notice, summons, complaint, lease, etc.)
- is_residential: Whether this appears to be a residential property (true/false)

Respond ONLY with a valid JSON object containing these fields.
"""


def extract_fields_from_documents(
    documents_text: list[dict],
    openai_client,
    model: str = "gpt-4o",
) -> dict:
    """Extract structured case fields from uploaded document text using AI.

    Args:
        documents_text: List of dicts with keys: doc_type, ocr_text, filename
        openai_client: OpenAI client instance
        model: OpenAI model to use

    Returns:
        dict with extracted fields
    """
    combined_text = ""
    for doc in documents_text:
        combined_text += f"\n--- Document: {doc['filename']} (Type: {doc['doc_type']}) ---\n"
        combined_text += doc.get('ocr_text', '') + "\n"

    if not combined_text.strip():
        return {"status": "error", "error": "No readable text found in documents"}

    try:
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": EXTRACTION_PROMPT},
                {"role": "user", "content": f"Here are the eviction documents:\n\n{combined_text[:50000]}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        raw = response.choices[0].message.content
        extracted = json.loads(raw)

        # Clean up - convert date strings to proper format
        date_fields = ["notice_date", "service_date", "court_date", "response_deadline"]
        for field in date_fields:
            if extracted.get(field):
                extracted[field] = _normalize_date(extracted[field])

        if extracted.get("amount_claimed"):
            extracted["amount_claimed"] = _normalize_amount(extracted["amount_claimed"])

        return {"status": "success", "fields": extracted}

    except Exception as e:
        logger.error(f"AI extraction failed: {e}")
        return {"status": "error", "error": str(e)}


def merge_intake_and_extraction(
    intake_data: dict,
    extraction_result: dict,
) -> dict:
    """Merge intake answers with AI-extracted data.

    Strategy:
    - For each field, prefer the document extraction if available and clear
    - Flag conflicts between intake and extraction for the confirmation screen
    """
    merged = {}
    conflicts = []
    fields = extraction_result.get("fields", {})

    for key in ["county", "case_number", "court_name", "landlord_name",
                 "property_address"]:
        intake_val = intake_data.get(key)
        extracted_val = fields.get(key)

        if intake_val and extracted_val and str(intake_val).lower() != str(extracted_val).lower():
            conflicts.append({
                "field": key,
                "intake_value": intake_val,
                "document_value": extracted_val,
                "resolved": False,
            })

        merged[key] = extracted_val or intake_val

    for key in ["amount_claimed", "notice_date", "service_date",
                 "court_date", "response_deadline"]:
        merged[key] = fields.get(key) or intake_data.get(key)

    return {
        "merged": merged,
        "conflicts": conflicts,
        "has_conflicts": len(conflicts) > 0,
    }


def _normalize_date(date_val: str) -> Optional[str]:
    """Try to parse and normalize a date string to YYYY-MM-DD."""
    formats = [
        "%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y",
        "%B %d, %Y", "%b %d, %Y",
        "%d-%b-%Y", "%d %B %Y",
    ]
    for fmt in formats:
        try:
            return datetime.strptime(date_val.strip(), fmt).strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            continue
    return date_val


def _normalize_amount(amount_val) -> Optional[float]:
    """Convert amount string to float."""
    if amount_val is None:
        return None
    if isinstance(amount_val, (int, float)):
        try:
            return float(amount_val)
        except (ValueError, TypeError):
            return None
    try:
        cleaned = str(amount_val).replace("$", "").replace(",", "").strip()
        return float(cleaned)
    except (ValueError, AttributeError):
        return None
