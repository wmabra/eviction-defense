#!/usr/bin/env python3
"""
Add fillable widgets to the OFFICIAL Oklahoma Pauper's Affidavit (flat PDF),
preserving the exact official form 1:1. Fillable fields are placed at the
exact blank positions so the filled form is court-accepted.
"""
import fitz

SRC = "app/templates/counties/ok_fee_waiver.pdf"
OUT = "app/templates/counties/ok_fee_waiver_fillable.pdf"

doc = fitz.open(SRC)


def add_widget(page, name, x, y, w, h, fontsize: float = 9):
    wd = fitz.Widget()
    wd.field_name = name  # type: ignore[attr-defined]
    wd.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    wd.rect = fitz.Rect(x, y, x + w, y + h)  # type: ignore[attr-defined]
    wd.field_value = ""  # type: ignore[attr-defined]
    wd.text_font = "Helv"  # type: ignore[attr-defined]
    wd.text_fontsize = fontsize  # type: ignore[attr-defined]
    page.add_widget(wd)


p1 = doc[0]
p2 = doc[1]

# ── Page 1: caption + personal + financial ──
add_widget(p1, "county", 300, 60, 130, 18)             # after "OF" in "IN THE DISTRICT COURT OF _____ COUNTY"
add_widget(p1, "plaintiff_name", 108, 118, 180, 18)    # blank line above "Plaintiff,"
add_widget(p1, "defendant_name", 108, 189, 180, 18)    # blank line above "Respondent."
add_widget(p1, "case_number", 385, 141, 160, 18)       # after "Case Number"
add_widget(p1, "full_name", 110, 246, 180, 18)         # after "Name:"
add_widget(p1, "property_address", 120, 270, 350, 18)  # after "Address:"
add_widget(p1, "employment_income", 200, 318, 80, 18)  # after "Salary or rate per hour: $"
add_widget(p1, "rent_or_mortgage", 310, 366, 80, 18)   # after "rent or mortgage payment? $"
add_widget(p1, "checking_balance", 165, 462, 80, 18)   # after "a. Bank Accounts: $"
add_widget(p1, "cash_on_hand", 165, 486, 80, 18)       # after "b. Cash on Hand: $"

# ── Page 2: assets + expenses + signature ──
add_widget(p2, "vehicle_value", 315, 145, 60, 18)      # after "Car $"
add_widget(p2, "utilities_expense", 200, 397, 60, 18)  # after "Electricity $"
add_widget(p2, "signature", 360, 649, 180, 18)         # "Sign Your Name" line
add_widget(p2, "printed_name", 360, 685, 180, 18)      # "Print Your Name" line

doc.save(OUT, deflate=True)
doc.close()
print(f"Created {OUT}")

# Verify
d = fitz.open(OUT)
widgets = [w for p in d for w in p.widgets()]
print(f"Widgets: {len(widgets)}")
for w in widgets:
    r = w.rect  # type: ignore[attr-defined]
    if r is not None:
        print(f"  {w.field_name}: page {w.parent}, ({r.x0:.0f},{r.y0:.0f})")  # type: ignore[attr-defined]
d.close()
