#!/usr/bin/env python3
"""
Add fillable form widgets to the OFFICIAL Oregon FED Answer form (or_eviction_answer_ref.pdf),
preserving the exact official OJD form 1:1.
"""
import pymupdf

SRC = "app/templates/counties/or_eviction_answer_ref.pdf"
OUT = "app/templates/counties/or_eviction_answer.pdf"

doc = pymupdf.open(SRC)


def add_text_widget(page, name, x, y, w, h, fontsize: float = 10, multiline: bool = False):
    wd = pymupdf.Widget()
    wd.field_name = name
    wd.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT
    wd.rect = pymupdf.Rect(x, y, x + w, y + h)
    wd.field_value = ""
    wd.text_font = "Helv"
    wd.text_fontsize = fontsize
    if multiline:
        wd.field_flags = pymupdf.PDF_TX_FIELD_IS_MULTILINE
    page.add_widget(wd)


def add_checkbox_widget(page, name, x, y, w=10.2, h=10.2):
    wd = pymupdf.Widget()
    wd.field_name = name
    wd.field_type = pymupdf.PDF_WIDGET_TYPE_CHECKBOX
    wd.rect = pymupdf.Rect(x, y, x + w, y + h)
    wd.field_value = False
    page.add_widget(wd)


p1 = doc[0]
p2 = doc[1]

# ── Page 1: Caption ──
add_text_widget(p1, "county", 285, 82, 147, 15, fontsize=10)
add_text_widget(p1, "plaintiff_name", 72, 137, 240, 16, fontsize=10)
add_text_widget(p1, "case_number", 400, 138, 140, 16, fontsize=10)
add_text_widget(p1, "defendant_name", 72, 206, 240, 16, fontsize=10)

# ── Page 1: Defenses ──
add_checkbox_widget(p1, "defense_repairs", 91.1, 293.3)
add_text_widget(p1, "defense_repairs_narrative", 108, 303, 430, 14, fontsize=8.5)
add_checkbox_widget(p1, "defense_corrected", 91.1, 336.4)
add_checkbox_widget(p1, "defense_retaliation", 91.1, 348.8)
add_checkbox_widget(p1, "defense_discrimination", 91.1, 373.8)
add_checkbox_widget(p1, "defense_paid", 91.1, 398.9)
add_checkbox_widget(p1, "defense_attempted_pay", 91.1, 411.4)
add_checkbox_widget(p1, "defense_rental_assistance", 109.1, 436.3)
add_checkbox_widget(p1, "defense_bad_notice", 91.1, 448.8)
add_text_widget(p1, "defense_bad_notice_narrative", 298, 445, 242, 13, fontsize=7.5)
add_checkbox_widget(p1, "defense_other", 91.1, 461.4)
add_text_widget(p1, "defense_other_narrative", 226, 458, 312, 13, fontsize=8.5)
add_checkbox_widget(p1, "defense_pages_attached", 109.1, 486.5)

# ── Page 1: Tenant 1 Signature & Contact Block ──
add_text_widget(p1, "signature", 72, 610, 144, 15, fontsize=9)
add_text_widget(p1, "printed_name", 252, 610, 180, 15, fontsize=9.5)
add_text_widget(p1, "date", 468, 610, 72, 15, fontsize=9.5)
add_text_widget(p1, "property_address", 72, 647, 175, 15, fontsize=8.5)
add_text_widget(p1, "city_state_zip", 252, 647, 210, 15, fontsize=9.5)
add_text_widget(p1, "phone", 468, 647, 72, 15, fontsize=9.5)
add_text_widget(p1, "email", 72, 684, 468, 16, fontsize=9.5)

# ── Page 2: Certificate of Mailing ──
add_text_widget(p2, "cert_date", 186, 270, 138, 15, fontsize=9.5)
add_text_widget(p2, "cert_landlord_address", 72, 308, 468, 15, fontsize=9.5)
add_text_widget(p2, "cert_date_sig", 72, 345, 108, 15, fontsize=9.5)
add_text_widget(p2, "cert_signature", 288, 345, 252, 15, fontsize=9)
add_text_widget(p2, "cert_name", 288, 382, 252, 15, fontsize=9.5)

doc.save(OUT)
print(f"Saved fillable answer form with widgets to {OUT}")
