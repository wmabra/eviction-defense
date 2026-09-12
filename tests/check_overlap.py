#!/usr/bin/env python3
"""Detect filled-text overlap deterministically — no OCR, flip-agnostic.

Renders the blank form to a grayscale image and, for each filled widget, checks
whether the widget's rendered region contains a *tall band* of printed ink
(text), as opposed to a thin underline (which the value is supposed to sit on).

This works in rendered pixel space, so it is immune to the y-flip that some
rebuilt/scanned forms store in their text layer.

`Widget.rect` (PyMuPDF) is top-down (y=0 = top) and matches the rendered
position, so no coordinate conversion is needed.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")
import fitz

TEXT = getattr(fitz, "PDF_WIDGET_TYPE_TEXT", 7)
DPI = 96
_THIN_LINE_PX = 4  # an underline is ~1-2pt (1-3px at 96dpi); text is much taller


def _region_has_text_ink(samples, width, height, px0, py0, px1, py1) -> bool:
    """True if the pixel region contains a vertical band of ink taller than an
    underline (i.e. printed text, not a blank line)."""
    px0 = max(0, px0); py0 = max(0, py0)
    px1 = min(width, px1); py1 = min(height, py1)
    if px1 <= px0 or py1 <= py0:
        return False
    max_run = run = 0
    for y in range(py0, py1):
        row = samples[y * width + px0: y * width + px1]
        if any(b < 160 for b in row):
            run += 1
            max_run = max(max_run, run)
        else:
            run = 0
    return max_run > _THIN_LINE_PX


def check_overlap(filled_path: str, blank_form_path: str) -> list:
    """Return a list of overlap descriptions: a filled value sits on printed text."""
    blank = fitz.open(blank_form_path)
    filled = fitz.open(filled_path)
    overlaps = []
    scale = DPI / 72.0
    for pno in range(min(blank.page_count, filled.page_count)):
        # annots=False hides the blank form's own field default values (e.g. a
        # pre-printed "CLARK" county or "$0" totals), which the fill REPLACES
        # rather than overlaps.
        pix = blank[pno].get_pixmap(dpi=DPI, colorspace=fitz.csGRAY, annots=False)
        samples = pix.samples
        w, h = pix.width, pix.height
        for wdg in filled[pno].widgets():
            if getattr(wdg, "field_type", None) != TEXT:
                continue
            val = str(getattr(wdg, "field_value", "") or "").strip()
            if not val:
                continue
            r = wdg.rect  # top-down, rendered
            if r is None or r.is_empty:
                continue
            fs = getattr(wdg, "text_fontsize", None) or 10.0
            vw = fitz.get_text_length(val, fontname="helv", fontsize=fs)
            # value text extent (left-aligned): x from r.x0, width = text width
            x0 = r.x0
            x1 = min(r.x0 + vw, r.x1)
            # check the widget's full height band
            px0 = int(x0 * scale); px1 = int(x1 * scale)
            py0 = int(r.y0 * scale); py1 = int(r.y1 * scale)
            if _region_has_text_ink(samples, w, h, px0, py0, px1, py1):
                overlaps.append(
                    f"page {pno}: '{getattr(wdg,'field_name','')}'=({val[:25]!r}) "
                    f"sits on printed text")
    blank.close()
    filled.close()
    return overlaps


if __name__ == "__main__":
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
