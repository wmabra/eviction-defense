#!/usr/bin/env python3
"""Detect filled-text overlap: does filled text land on top of the form's printed text?"""
import os, sys, io
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
import fitz
import pytesseract
from PIL import Image

TEXT = getattr(fitz, "PDF_WIDGET_TYPE_TEXT", 7)

def ocr_words(page, dpi=150):
    """Return [(Rect, text)] of printed words on a page (bottom-left coords)."""
    pix = page.get_pixmap(dpi=dpi)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    scale = page.rect.height / pix.height
    words = []
    for i in range(len(data["text"])):
        t = data["text"][i].strip()
        if not t or int(data["conf"][i]) < 40:
            continue
        x = int(data["left"][i]) * scale
        y_top = int(data["top"][i]) * scale
        w = int(data["width"][i]) * scale
        h = int(data["height"][i]) * scale
        y_bottom = page.rect.height - y_top  # OCR y is top-down; convert to bottom-up
        words.append((fitz.Rect(x, y_bottom - h, x + w, y_bottom), t))
    return words


def check_overlap(filled_path, blank_form_path):
    """Return list of overlap descriptions: filled widget value sits on printed text."""
    blank = fitz.open(blank_form_path)
    filled = fitz.open(filled_path)
    overlaps = []
    for pno in range(min(blank.page_count, filled.page_count)):
        printed = ocr_words(blank[pno])
        for w in filled[pno].widgets():
            if getattr(w, "field_type", None) != TEXT:
                continue
            val = str(getattr(w, "field_value", "") or "").strip()
            if not val:
                continue
            r = w.rect
            for pr, pt in printed:
                if r.intersects(pr):
                    overlaps.append(f"page {pno}: '{getattr(w,'field_name','')}'=({val[:25]!r}) overlaps printed '{pt}'")
    blank.close()
    filled.close()
    return overlaps


if __name__ == "__main__":
    # quick self-test on a freshly generated AR answer form
    from app.services.pdf_overlay import fill_answer_form
    data = {
        "personal_info": {"full_name": "John Doe", "county": "Benton", "property_address": "123 Main St",
                          "property_city": "Benton", "property_zip": "72015", "phone": "(555) 123-4567",
                          "email": "johndoe@example.com"},
        "landlord_info": {"landlord_name": "Smith Property Management, LLC"},
        "case_details": {"case_number": "CV-2026-00123", "court_name": "Benton County District Court"},
        "defenses": {"def_repairs": {"checked": True}, "def_bad_notice": {"checked": True}, "def_amount": {"checked": True}},
        "financial_info": {},
    }
    fill_answer_form(data, "AR", "/tmp/ar_ans_test.pdf")
    overlaps = check_overlap("/tmp/ar_ans_test.pdf", "app/templates/counties/ar_eviction_answer.pdf")
    print(f"AR answer form: {len(overlaps)} overlaps")
    for o in overlaps[:30]:
        print("  " + o)
