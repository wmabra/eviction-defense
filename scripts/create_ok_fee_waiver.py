#!/usr/bin/env python3
"""
Create a fillable Oklahoma Pauper's Affidavit (fee waiver) form.

The official Oklahoma Pauper's Affidavit is a flat form; this recreates its
court-accepted structure as a fillable PDF with standardized field names.
"""
import fitz

OUT = "app/templates/counties/ok_fee_waiver.pdf"

doc = fitz.open()
page = doc.new_page(width=612, height=792)


def text(x, y, s, size: float = 10, bold: bool = False):
    font = "hebo" if bold else "helv"
    page.insert_text(fitz.Point(x, y), s, fontsize=size, fontname=font)


def field(name, x, y, w, h, fontsize: float = 9):
    wd = fitz.Widget()
    wd.field_name = name  # type: ignore[attr-defined]
    wd.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    wd.rect = fitz.Rect(x, y, x + w, y + h)  # type: ignore[attr-defined]
    wd.field_value = ""  # type: ignore[attr-defined]
    wd.text_font = "Helv"  # type: ignore[attr-defined]
    wd.text_fontsize = fontsize  # type: ignore[attr-defined]
    page.add_widget(wd)


# ── Caption ──────────────────────────────────────────────
text(72, 55, "IN THE DISTRICT COURT OF", 11)
lead = fitz.get_text_length("COUNTY, STATE OF OKLAHOMA — ", fontname="helv", fontsize=11)
text(72, 72, "COUNTY, STATE OF OKLAHOMA — ")
field("county", 72 + lead, 60, 130, 16, 10)

field("plaintiff_name", 72, 110, 250, 16, 10)
text(72, 130, "Plaintiff,", 10)
text(400, 112, "CASE NO.", 9)
field("case_number", 440, 107, 120, 16, 10)

text(72, 155, "vs.", 10)
field("defendant_name", 72, 180, 250, 16, 10)
text(72, 200, "Respondent.", 10)

# ── Title ────────────────────────────────────────────────
text(72, 235, "PAUPER'S AFFIDAVIT", 13, bold=True)

# ── Personal ─────────────────────────────────────────────
text(72, 265, "Name:", 10)
field("full_name", 115, 257, 280, 16, 10)
text(72, 285, "Address:", 10)
field("property_address", 120, 277, 400, 16, 10)
text(72, 305, "Phone:", 10)
field("phone", 115, 297, 160, 16, 10)
text(72, 325, "Number of persons living with you (dependents):", 10)
field("total_dependents", 340, 317, 50, 16, 10)

# ── Income ───────────────────────────────────────────────
text(72, 355, "1. Monthly gross salary / wages:", 10)
field("employment_income", 270, 347, 100, 16, 10)
text(72, 380, "2. Monthly rent or mortgage payment:", 10)
field("rent_or_mortgage", 270, 372, 100, 16, 10)

# ── Financial Resources ──────────────────────────────────
text(72, 410, "3. FINANCIAL RESOURCES:", 10, bold=True)
text(90, 428, "a. Bank Accounts:", 10)
field("checking_balance", 200, 420, 90, 16, 10)
text(90, 448, "b. Cash on Hand:", 10)
field("cash_on_hand", 200, 440, 90, 16, 10)
text(90, 468, "c. Value of car:", 10)
field("vehicle_value", 200, 460, 90, 16, 10)

# ── Expenses ─────────────────────────────────────────────
text(72, 500, "4. Monthly utility bills:", 10, bold=True)
text(90, 518, "Electricity/Gas/Water/Phone:", 10)
field("utilities_expense", 260, 510, 90, 16, 10)
text(90, 538, "Food:", 10)
field("food_expense", 130, 530, 90, 16, 10)
text(90, 558, "Medical:", 10)
field("medical_expense", 130, 550, 90, 16, 10)

# ── Affirmation ──────────────────────────────────────────
text(72, 600, "I swear (or affirm) that I am without funds or other sources of income to pay the", 9.5)
text(84, 615, "costs of this case. I understand that a knowingly false statement may be perjury.", 9.5)

text(72, 650, "DATED: __________________", 10)
field("date", 150, 637, 110, 16, 10)

text(72, 690, "______________________________________", 10)
field("signature", 72, 676, 250, 16, 10)
text(72, 710, "Signature", 9)

field("printed_name", 72, 728, 250, 16, 10)
text(72, 748, "Printed Name", 9)

doc.save(OUT, deflate=True)
doc.close()
print(f"Created fillable form: {OUT}")

d = fitz.open(OUT)
widgets = list(d[0].widgets())
print(f"Widgets: {len(widgets)}")
for w in widgets:
    r = w.rect  # type: ignore[attr-defined]
    if r is not None:
        print(f"  {w.field_name}: ({r.x0:.0f},{r.y0:.0f})")  # type: ignore[attr-defined]
d.close()
