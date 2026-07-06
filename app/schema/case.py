"""Pydantic models for case profiles and AI extraction results."""
from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, Field


class CaseProfile(BaseModel):
    """Full case profile combining intake + extracted data."""
    case_id: str
    status: str
    created_at: datetime
    pre_screen: dict
    personal_info: Optional[dict] = None
    landlord_info: Optional[dict] = None
    case_details: Optional[dict] = None
    defenses: Optional[dict] = None
    preferences: Optional[dict] = None
    extracted_data: Optional[dict] = None
    extraction_confirmed: bool = False
    packet_status: str = "not_generated"


class ExtractedField(BaseModel):
    """A single field extracted from a document, with source tracking."""
    value: str | float | date | None = None
    source: str = "intake"  # intake, document, or conflict
    confirmed: bool = False


class ExtractionResult(BaseModel):
    """AI extraction output from uploaded documents."""
    status: str = "pending"  # pending, processing, ready, conflict
    fields: dict[str, ExtractedField]


class DocumentAnalysis(BaseModel):
    """Result of OCR + AI analysis on a single uploaded document."""
    doc_type: str
    filename: str
    ocr_success: bool
    page_count: int
    extracted_data: dict


class CaseStatus(BaseModel):
    case_id: str
    status: str
    stage: str  # pre_screen, payment_pending, intake, extraction, confirmation, packet_ready, delivered
    next_action: str  # What the customer needs to do next
    message: str
