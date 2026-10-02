#!/usr/bin/env python3
"""
Add fillable form widgets to the OFFICIAL Oregon Fee Deferral or Waiver Application & Order (or_fee_waiver_ref.pdf),
preserving the exact official OJD form 1:1.
"""
import pymupdf

SRC = "app/templates/counties/or_fee_waiver_ref.pdf"
OUT = "app/templates/counties/or_fee_waiver.pdf"

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
p3 = doc[2]
p4 = doc[3]
p5 = doc[4]

# ── Page 1: Application Caption & Initial Options ──
add_text_widget(p1, "county", 305, 82, 127, 15, fontsize=10)
add_text_widget(p1, "plaintiff_name", 72, 109, 243, 15, fontsize=10)
add_text_widget(p1, "case_number", 395, 109, 150, 15, fontsize=10)
add_text_widget(p1, "defendant_name", 72, 164, 243, 15, fontsize=10)
add_text_widget(p1, "full_name", 186, 215, 354, 15, fontsize=10)
add_checkbox_widget(p1, "role_defendant", 236.8, 282.5, 10.2, 10.2)
add_checkbox_widget(p1, "fee_filing", 109.1, 319.9, 10.2, 10.2)
add_checkbox_widget(p1, "fee_response", 335.2, 319.9, 10.2, 10.2)

# ── Page 2: Household, Public Benefits, Income, Assets ──
add_text_widget(p2, "household_size", 317, 178, 54, 15, fontsize=10)
add_checkbox_widget(p2, "legal_aid_no", 109.1, 249.0, 10.2, 10.2)
add_checkbox_widget(p2, "legal_aid_yes", 109.1, 261.5, 10.2, 10.2)
add_checkbox_widget(p2, "receives_snap", 131.5, 327.5, 9.1, 9.1)
add_text_widget(p2, "snap_amount", 450, 321, 65, 15, fontsize=9)
add_checkbox_widget(p2, "receives_ssi", 131.5, 338.9, 9.1, 9.1)
add_text_widget(p2, "ssi_amount", 321, 332, 50, 15, fontsize=9)
add_checkbox_widget(p2, "receives_tanf", 131.5, 350.3, 9.1, 9.1)
add_text_widget(p2, "tanf_amount", 374, 344, 68, 15, fontsize=9)
add_checkbox_widget(p2, "receives_medicaid", 131.5, 361.7, 9.1, 9.1)
add_text_widget(p2, "total_benefits", 289, 378, 82, 15, fontsize=9)
add_text_widget(p2, "employment_income", 420, 444, 95, 15, fontsize=9.5)
add_text_widget(p2, "other_income", 330, 466, 112, 15, fontsize=9.5)
add_text_widget(p2, "total_monthly_income", 331, 507, 112, 15, fontsize=9.5)
add_text_widget(p2, "cash_on_hand", 277, 548, 77, 15, fontsize=9.5)
add_text_widget(p2, "asset_desc_1", 72, 594, 468, 15, fontsize=9)
add_text_widget(p2, "asset_value", 189, 656, 74, 15, fontsize=9.5)
add_text_widget(p2, "total_assets", 306, 681, 90, 15, fontsize=9.5)

# ── Page 3: Living Expenses & Applicant Signature ──
add_text_widget(p3, "home_expense", 233, 92, 102, 15, fontsize=9.5)
add_text_widget(p3, "transportation_expense", 233, 129, 102, 15, fontsize=9.5)
add_text_widget(p3, "other_expenses", 233, 165, 102, 15, fontsize=9.5)
add_text_widget(p3, "total_monthly_expenses", 301, 199, 93, 15, fontsize=9.5)
add_text_widget(p3, "date", 72, 383, 180, 15, fontsize=9.5)
add_text_widget(p3, "signature", 288, 383, 252, 15, fontsize=9)
add_text_widget(p3, "printed_name", 288, 421, 252, 15, fontsize=9.5)
add_text_widget(p3, "property_address", 72, 458, 175, 15, fontsize=8.5)
add_text_widget(p3, "city_state_zip", 252, 458, 175, 15, fontsize=9.5)
add_text_widget(p3, "phone", 434, 458, 106, 15, fontsize=9.5)

# ── Page 4: Order Caption ──
add_text_widget(p4, "county_p4", 305, 82, 127, 15, fontsize=10)
add_text_widget(p4, "plaintiff_name_p4", 72, 109, 243, 15, fontsize=10)
add_text_widget(p4, "case_number_p4", 395, 109, 150, 15, fontsize=10)
add_text_widget(p4, "defendant_name_p4", 72, 164, 243, 15, fontsize=10)
add_text_widget(p4, "full_name_p4", 183, 218, 321, 14, fontsize=10)
add_checkbox_widget(p4, "order_fee_filing", 109.1, 262.2, 9.1, 9.1)

# ── Page 5: Order Certificate of Readiness ──
add_checkbox_widget(p5, "order_role_defendant", 247.4, 136.6, 10.2, 10.2)
add_text_widget(p5, "order_signature_1", 72, 153, 216, 15, fontsize=9)
add_text_widget(p5, "order_print_name_1", 360, 153, 180, 15, fontsize=9.5)
add_text_widget(p5, "order_date", 72, 253, 180, 15, fontsize=9.5)
add_text_widget(p5, "order_signature", 288, 253, 252, 15, fontsize=9)
add_text_widget(p5, "order_printed_name", 288, 291, 252, 15, fontsize=9.5)
add_text_widget(p5, "order_address", 72, 328, 175, 15, fontsize=8.5)
add_text_widget(p5, "order_city_state_zip", 252, 328, 175, 15, fontsize=9.5)
add_text_widget(p5, "order_phone", 432, 328, 108, 15, fontsize=9.5)

doc.save(OUT)
print(f"Saved fillable fee waiver form with widgets to {OUT}")
