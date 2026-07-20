"""Document upload and AI extraction API endpoints."""
import json
import os
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import JSONResponse, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.database.models import Case, Document
from app.config import settings
from app.services.gates import check_document_quality, check_all_document_quality
from app.services.confirmation import build_confirmation_screen, process_confirmation_submission

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["documents"])

UPLOAD_DIR = "app/static/uploads"


# ======================== DOCUMENT UPLOAD ========================

@router.post("/upload/{case_id}")
async def upload_document(
    case_id: str,
    file: UploadFile = File(...),
    doc_type: str = Form(...),
    db: Session = Depends(get_db),
):
    """Upload a single eviction document for a case.

    Accepts PDF, JPG, PNG. Stores file and saves database record.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Validate file type
    allowed_types = {".pdf", ".jpg", ".jpeg", ".png"}
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type {ext} not supported. Use PDF, JPG, or PNG.",
        )

    # Save file
    case_dir = os.path.join(UPLOAD_DIR, case_id)
    os.makedirs(case_dir, exist_ok=True)
    safe_filename = f"{doc_type}_{file.filename}"
    filepath = os.path.join(case_dir, safe_filename)

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    # Save document record
    doc = Document(
        case_id=case_id,
        doc_type=doc_type,
        filename=file.filename,
        filepath=filepath,
    )
    db.add(doc)
    case.status = "extraction_pending"
    db.commit()

    return {
        "status": "ok",
        "document_id": doc.id,
        "filename": file.filename,
        "doc_type": doc_type,
        "file_size": len(content),
    }


@router.post("/extract/{case_id}")
def run_extraction(case_id: str, db: Session = Depends(get_db)):
    """Run AI extraction on all uploaded documents for a case.

    This is the core intelligence pipeline:
    1. Load uploaded documents
    2. Run OCR on each (Google Document AI if configured, else fallback)
    3. Check document quality (Gate 1)
    4. Send to OpenAI for structured extraction
    5. Merge with intake data
    6. Return confirmation screen payload
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    documents = db.query(Document).filter(Document.case_id == case_id).all()
    if not documents:
        raise HTTPException(status_code=400, detail="No documents uploaded yet")

    # Step 1: OCR each document
    doc_texts = []
    for doc in documents:
        ocr_text = _run_ocr(doc.filepath, doc.doc_type)
        doc.ocr_text = ocr_text
        doc.ocr_processed = True
        doc_texts.append({
            "doc_type": doc.doc_type,
            "filename": doc.filename,
            "ocr_text": ocr_text,
        })

    # Step 2: Document quality check (Gate 1)
    quality_results = check_all_document_quality(doc_texts)
    failed_quality = [r for r in quality_results if not r.passed]
    if failed_quality:
        db.commit()
        return {
            "status": "quality_issue",
            "message": failed_quality[0].message,
            "requires_action": True,
        }

    # Step 3: AI extraction
    extraction_result = _run_ai_extraction(doc_texts)
    if extraction_result.get("status") == "error":
        db.commit()
        return {
            "status": "extraction_error",
            "message": f"AI extraction failed: {extraction_result.get('error', 'Unknown error')}",
        }

    # Step 4: Merge with intake data
    intake_data = _build_intake_dict(case)
    merged = _merge_intake_and_extraction(intake_data, extraction_result)

    # Step 5: Build confirmation screen
    confirmation = build_confirmation_screen(intake_data, extraction_result)

    # Save extracted data to case record
    case.extracted_data = json.dumps(extraction_result.get("fields", {}))
    case.status = "confirmation_pending"
    db.commit()

    return {
        "status": "ready",
        "extraction": extraction_result.get("fields", {}),
        "conflicts": merged.get("conflicts", []),
        "has_conflicts": merged.get("has_conflicts", False),
        "confirmation_screen": confirmation,
    }


@router.get("/extraction-status/{case_id}")
def get_extraction_status(case_id: str, db: Session = Depends(get_db)):
    """Get the current extraction status and results for a case."""
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    documents = db.query(Document).filter(Document.case_id == case_id).all()
    docs_status = [
        {
            "id": d.id,
            "type": d.doc_type,
            "filename": d.filename,
            "ocr_processed": d.ocr_processed,
        }
        for d in documents
    ]

    extracted = {}
    if case.extracted_data:
        try:
            extracted = json.loads(case.extracted_data)
        except (json.JSONDecodeError, TypeError):
            extracted = {}

    return {
        "case_id": case_id,
        "status": case.status,
        "documents": docs_status,
        "extraction_confirmed": case.extraction_confirmed,
        "extracted_data": extracted,
    }


@router.post("/confirm/{case_id}")
def confirm_extraction(
    case_id: str,
    confirmed_fields: dict,
    confirmation_signed: bool = True,
    db: Session = Depends(get_db),
):
    """Process the customer's confirmation of extracted data.

    This is the step that replaces the human QA person.
    The customer must confirm every field before documents are generated.
    """
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    result = process_confirmation_submission(confirmed_fields, confirmation_signed)
    if not result.get("valid"):
        return {"status": "validation_error", "errors": result.get("errors", [])}

    case.extraction_confirmed = True
    case.status = "confirmation_complete"
    db.commit()

    return {
        "status": "confirmed",
        "message": "All fields confirmed. Packet generation will begin.",
        "case_id": case_id,
    }


# ======================== INTERNAL HELPERS ========================

def _run_ocr(filepath: str, doc_type: str) -> str:
    """Run OCR on a document.

    Uses Google Document AI if configured, otherwise extracts text from PDF
    metadata or returns a placeholder for images.

    In production, replace this with Google Cloud Document AI:
        from google.cloud import documentai
        client = documentai.DocumentProcessorServiceClient()
        ...
    """
    ext = os.path.splitext(filepath)[1].lower()

    try:
        # PDF text extraction (for text-based PDFs)
        if ext == ".pdf":
            try:
                import PyPDF2
                with open(filepath, "rb") as f:
                    reader = PyPDF2.PdfReader(f)
                    text = ""
                    for page in reader.pages:
                        text += page.extract_text() or ""
                    if text.strip():
                        return text
            except ImportError:
                pass

            # Try pdfminer as fallback
            try:
                from pdfminer.high_level import extract_text as pdfminer_extract
                text = pdfminer_extract(filepath)
                if text.strip():
                    return text
            except ImportError:
                pass

        # For images, try pytesseract
        if ext in (".jpg", ".jpeg", ".png"):
            try:
                from PIL import Image
                import pytesseract
                image = Image.open(filepath)
                text = pytesseract.image_to_string(image)
                if text.strip():
                    return text
            except ImportError:
                pass

    except Exception as e:
        logger.warning(f"OCR failed for {filepath}: {e}")

    # Fallback: extract filename-based hint
    return f"[Document uploaded: {os.path.basename(filepath)} (type: {doc_type})]"


def _run_ai_extraction(doc_texts: list[dict]) -> dict:
    """Run AI extraction on document texts.

    Supports any OpenAI-compatible API (DeepSeek, OpenAI, etc.).
    Configure via .env:
        LLM_API_KEY=sk-...
        LLM_BASE_URL=https://api.deepseek.com/v1
        LLM_MODEL=deepseek-chat
    
    If no key is configured, falls back to regex extraction (free).
    """
    if settings.llm_api_key:
        try:
            from openai import OpenAI
            client = OpenAI(
                api_key=settings.llm_api_key,
                base_url=settings.llm_base_url,
            )
            from app.services.extraction import extract_fields_from_documents
            result = extract_fields_from_documents(
                doc_texts, client, model=settings.llm_model
            )
            if result.get("status") == "success":
                return result
            logger.warning(f"LLM extraction returned error, using fallback: {result.get('error')}")
        except Exception as e:
            logger.warning(f"LLM extraction failed, using fallback: {e}")

    # Fallback: regex extraction for development (free, no API key needed)
    logger.info("No LLM API key configured, using regex fallback extraction")
    return _simulated_extraction(doc_texts)


def _simulated_extraction(doc_texts: list[dict]) -> dict:
    """Simulated extraction for development when no API keys are set.

    Scans OCR text for patterns like case numbers, amounts, dates.
    """
    import re

    combined = " ".join(d.get("ocr_text", "") for d in doc_texts)

    fields = {}

    # Case number pattern: e.g. CACE-24-012345
    case_match = re.search(r'[A-Z]+-\d{2,4}-\d+', combined)
    if case_match:
        fields["case_number"] = case_match.group(0)

    # Dollar amounts
    amount_match = re.search(r'\$[\d,]+\.?\d*', combined)
    if amount_match:
        fields["amount_claimed"] = amount_match.group(0)

    # Dates
    date_match = re.search(r'\d{1,2}/\d{1,2}/\d{2,4}', combined)
    if date_match:
        fields["service_date"] = date_match.group(0)

    # County detection
    counties = ["Miami-Dade", "Broward", "Duval", "Hillsborough", "Orange",
                 "Palm Beach", "Polk", "Pinellas", "Volusia", "Lee",
                 "Leon", "Seminole", "Osceola", "Pasco", "Brevard"]
    for county in counties:
        if county.lower() in combined.lower():
            fields["county"] = county
            break

    return {"status": "success", "fields": fields}


def _merge_intake_and_extraction(intake_data: dict, extraction_result: dict) -> dict:
    """Merge intake data with AI extraction results.

    Flags conflicts for the confirmation screen.
    """
    merged = {}
    conflicts = []
    fields = extraction_result.get("fields", {})

    for key in ["county", "case_number", "court_name", "landlord_name",
                 "property_address", "full_name"]:
        intake_val = intake_data.get(key)
        extracted_val = fields.get(key)

        if intake_val and extracted_val and str(intake_val).lower() != str(extracted_val).lower():
            conflicts.append({
                "field": key,
                "intake_value": intake_val,
                "document_value": extracted_val,
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


@router.get("/generate-packet")
def generate_packet(
    full_name: str,
    county: str,
    state: str = "FL",
    property_address: str = "",
    landlord_name: str = "",
    case_number: str = "",
    phone: str = "",
    email: str = "",
):
    """Generate a complete eviction defense packet with all documents."""
    import tempfile, zipfile
    
    data = {
        "state": state.upper(),
        "personal_info": {
            "full_name": full_name,
            "property_address": property_address,
            "property_city": "",
            "county": county,
            "phone": phone,
            "email": email,
        },
        "landlord_info": {
            "landlord_name": landlord_name,
            "landlord_address": "",
            "landlord_phone": "",
            "landlord_email": "",
        },
        "case_details": {
            "case_number": case_number,
            "court_name": county,
            "complaint_amount_claimed": "",
        },
        "rent_payment": {"monthly_rent": ""},
        "defenses": {},
        "preferences": {"trial_by": "judge"},
    }
    
    # Generate all documents to a temp dir
    tmpdir = tempfile.mkdtemp()
    from app.services.generator import generate_packet as gen
    paths = gen(data, tmpdir)
    
    # Also fill the official court form if available
    try:
        from app.services.form_filler import fill_answer_form
        from app.services.pdf_overlay import fill_fee_waiver
        
        state_code = data.get("state", state.upper())
        court_pdf = os.path.join(tmpdir, "01_COURT_FORM_Answer_FILE_THIS.pdf")
        fill_answer_form(data, state_code, court_pdf)
        paths["court_form"] = court_pdf
        
        # Also fill fee waiver if tenant has financial info
        if data.get("financial_info"):
            fee_waiver_pdf = os.path.join(tmpdir, "02_COURT_FORM_Fee_Waiver_FILE_THIS.pdf")
            fill_fee_waiver(data, state_code, fee_waiver_pdf)
            paths["fee_waiver"] = fee_waiver_pdf
    except Exception as e:
        import logging
        logging.warning(f"Court form fill skipped: {e}")
    
    # Create zip file
    zip_path = tempfile.mktemp(suffix=".zip")
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for name, filepath in paths.items():
            if os.path.exists(filepath):
                zf.write(filepath, os.path.basename(filepath))
    
    safe_name = full_name.replace(' ', '_') if full_name else 'Tenant'
    return FileResponse(
        zip_path,
        media_type="application/zip",
        filename=f"eviction_defense_packet_{safe_name}.zip"
    )


def _build_intake_dict(case: Case) -> dict:
    """Build a dict of intake answers from the Case database model."""
    return {
        "full_name": case.full_name,
        "property_address": case.property_address,
        "county": case.county,
        "court_name": case.court_name,
        "case_number": case.case_number,
        "landlord_name": case.landlord_name,
        "amount_claimed": case.complaint_amount_claimed,
        "notice_date": None,
        "service_date": str(case.summons_service_date) if case.summons_service_date else None,
        "court_date": str(case.court_date) if case.court_date else None,
        "response_deadline": str(case.response_deadline) if case.response_deadline else None,
    }
