#!/usr/bin/env python3
"""
Create a fillable Ohio fee waiver (Form 20 — Civil Fee Waiver Affidavit).

Ohio Form 20 is a flat statewide form; this recreates its key fields as a
fillable PDF with standardized field names.
"""
import pymupdf

OUT = "app/templates/counties/oh_fee_waiver.pdf"

doc = pymupdf.open()
page = doc.new_page(width=612, height=792)


def text(x, y, s, size: float = 10, bold: bool = False):
    font = "hebo" if bold else "helv"
    page.insert_text(pymupdf.Point(x, y), s, fontsize=size, fontname=font)


def field(name, x, y, w, h, fontsize: float = 9):
    wd = pymupdf.Widget()
    wd.field_name = name  # type: ignore[attr-defined]
    wd.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    wd.rect = pymupdf.Rect(x, y, x + w, y + h)  # type: ignore[attr-defined]
    wd.field_value = ""  # type: ignore[attr-defined]
    wd.text_font = "Helv"  # type: ignore[attr-defined]
    wd.text_fontsize = fontsize  # type: ignore[attr-defined]
    page.add_widget(wd)


# ── Caption ──────────────────────────────────────────────
text(72, 55, "IN THE", 11)
field("court_name", 115, 42, 300, 16, 10)
field("county", 72, 64, 110, 16, 10)
text(188, 76, "COUNTY, OHIO", 11)

field("plaintiff_name", 72, 98, 250, 16, 10)
text(72, 126, "Plaintiff,", 10)
text(380, 107, "CASE NO.", 9)
field("case_number", 435, 95, 125, 16, 10)

text(72, 150, "vs.", 10)
field("defendant_name", 72, 168, 250, 16, 10)
text(72, 196, "Defendant.", 10)

# ── Title ────────────────────────────────────────────────
text(72, 225, "FINANCIAL DISCLOSURE / FEE-WAIVER AFFIDAVIT AND ORDER", 11, bold=True)

# ── Personal ─────────────────────────────────────────────
text(72, 255, "Applicant's Full Name:", 10)
field("full_name", 210, 247, 280, 16, 10)
text(72, 275, "Address:", 10)
field("property_address", 120, 267, 400, 16, 10)
text(72, 295, "Number in household:", 10)
field("total_dependents", 200, 287, 60, 16, 10)

# ── Monthly Income ───────────────────────────────────────
text(72, 330, "Gross Monthly Employment Income (before taxes):", 10)
field("employment_income", 320, 322, 110, 16, 10)
text(72, 355, "Total Monthly Income:", 10)
field("monthly_gross_income", 200, 347, 110, 16, 10)

# ── Liquid Assets ────────────────────────────────────────
text(72, 390, "Liquid Assets:", 10, bold=True)
text(90, 408, "Cash on Hand:", 10)
field("cash_on_hand", 180, 400, 90, 16, 10)
text(90, 428, "Checking/Savings:", 10)
field("checking_balance", 200, 420, 90, 16, 10)

# ── Monthly Expenses ─────────────────────────────────────
text(72, 465, "Monthly Expenses:", 10, bold=True)
text(90, 483, "Rent / Mortgage:", 10)
field("rent_or_mortgage", 190, 475, 90, 16, 10)
text(90, 503, "Utilities:", 10)
field("utilities_expense", 140, 495, 90, 16, 10)
text(90, 523, "Food:", 10)
field("food_expense", 130, 515, 90, 16, 10)
text(90, 543, "Transportation:", 10)
field("transportation_expense", 180, 535, 90, 16, 10)
text(90, 563, "Phone:", 10)
field("telephone_expense", 135, 550, 90, 16, 10)
text(90, 583, "Child Care:", 10)
field("child_care_expense", 160, 575, 90, 16, 10)
text(90, 603, "Medical:", 10)
field("medical_expense", 140, 595, 90, 16, 10)
text(90, 623, "Credit Cards / Loans:", 10)
field("debt_payments", 210, 615, 90, 16, 10)
text(90, 643, "Total Monthly Expenses:", 10)
field("total_monthly_expenses", 230, 635, 90, 16, 10)

# ── Certification / Signature ────────────────────────────
text(72, 680, "I certify that the information above is true and that I am unable to prepay costs.", 9)
text(72, 700, "DATED: __________________", 10)
field("date", 120, 687, 110, 16, 10)

page.draw_line(pymupdf.Point(72, 736), pymupdf.Point(320, 736))
field("signature", 72, 718, 248, 16, 10)
text(72, 748, "Signature", 9)

page.draw_line(pymupdf.Point(360, 736), pymupdf.Point(540, 736))
field("printed_name", 360, 718, 180, 16, 10)
text(360, 748, "Printed Name", 9)

doc.save(OUT, deflate=True)
doc.close()
print(f"Created fillable form: {OUT}")

d = pymupdf.open(OUT)
widgets = list(d[0].widgets())
print(f"Widgets: {len(widgets)}")
for w in widgets:
    r = w.rect  # type: ignore[attr-defined]
    if r is not None:
        print(f"  {w.field_name}: ({r.x0:.0f},{r.y0:.0f})")  # type: ignore[attr-defined]
d.close()
