#!/usr/bin/env python3
"""
Add fillable widgets to the OFFICIAL Oklahoma Pauper's Affidavit (flat PDF),
preserving the exact official form 1:1. Fillable fields are placed at the
exact blank positions so the filled form is court-accepted.
"""
import pymupdf

SRC = "app/templates/counties/ok_fee_waiver.pdf"
OUT = "app/templates/counties/ok_fee_waiver_fillable.pdf"

doc = pymupdf.open(SRC)


def add_widget(page, name, x, y, w, h, fontsize: float = 9):
    wd = pymupdf.Widget()
    wd.field_name = name  # type: ignore[attr-defined]
    wd.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    wd.rect = pymupdf.Rect(x, y, x + w, y + h)  # type: ignore[attr-defined]
    wd.field_value = ""  # type: ignore[attr-defined]
    wd.text_font = "Helv"  # type: ignore[attr-defined]
    wd.text_fontsize = fontsize  # type: ignore[attr-defined]
    page.add_widget(wd)


p1 = doc[0]
p2 = doc[1]
p3 = doc[2]

# ── Page 1: caption + personal + financial ──
add_widget(p1, "county", 296, 66, 112, 16)             # after "OF" in "IN THE DISTRICT COURT OF _____ COUNTY"
add_widget(p1, "plaintiff_name", 72, 120, 210, 16)     # blank line above "Plaintiff,"
add_widget(p1, "case_number", 390, 148, 120, 16)       # after "Case Number"
add_widget(p1, "defendant_name", 72, 186, 210, 16)     # blank line above "Respondent."
add_widget(p1, "full_name", 108, 253, 160, 16)         # after "Name:"
add_widget(p1, "property_address", 115, 277, 400, 16)  # after "Address:"

# Item 1: Employment
add_widget(p1, "employed_yes", 180, 304, 15, 14)       # "__ Yes"
add_widget(p1, "employed_no", 220, 304, 15, 14)        # "__ No"
add_widget(p1, "employer_name", 380, 301, 140, 16)     # "If so, who do you work for?"
add_widget(p1, "employment_income", 204, 328, 64, 16)  # after "Salary or rate per hour: $"

# Item 2: Residence & Household
add_widget(p1, "residence_rent", 128, 352, 15, 14)     # "___ rent"
add_widget(p1, "residence_own", 184, 352, 15, 14)      # "__ own"
add_widget(p1, "rent_or_mortgage", 304, 376, 66, 16)   # after "rent or mortgage payment? $"
add_widget(p1, "household_members", 90, 421, 430, 16)  # line below "List the names of the persons living with you..."

# Item 3: Financial Resources
add_widget(p1, "checking_balance", 188, 472, 55, 16)   # after "a. Bank Accounts: $"
add_widget(p1, "cash_on_hand", 188, 496, 55, 16)       # after "b. Cash on Hand: $"

# ── Page 2: assets + expenses + signature ──
add_widget(p2, "real_estate_value", 145, 153, 45, 16)  # after "Home $"
add_widget(p2, "vehicle_value", 237, 153, 45, 16)      # after "Car $"

# Item 4: Debts
add_widget(p2, "creditor_1", 95, 262, 135, 16)         # CREDITOR line 1
add_widget(p2, "debt_balance_1", 293, 262, 45, 16)     # BALANCE line 1 (after $)
add_widget(p2, "debt_payment_1", 418, 262, 45, 16)     # MO. PAYMENT line 1 (after $)

# Utilities
add_widget(p2, "utilities_expense", 170, 406, 45, 16)  # after "Electricity $"
add_widget(p2, "telephone_expense", 377, 406, 45, 16)  # after "Phone $"

# Signature
add_widget(p2, "signature", 360, 653, 160, 16)         # "Sign Your Name" line
add_widget(p2, "printed_name", 360, 689, 160, 16)      # "Print Your Name" line

# ── Page 3: Order relating to court costs ──
add_widget(p3, "printed_name_order", 72, 422, 200, 16)    # "Print Your Name" line
add_widget(p3, "property_address_order", 72, 457, 200, 16) # "Print Your Address" line
add_widget(p3, "city_state_zip_order", 72, 491, 200, 16) # "City, State, Zip Code" line
add_widget(p3, "phone_order", 72, 526, 200, 16)          # "Print Your Phone Number" line

doc.save(OUT, deflate=True)
doc.close()
print(f"Created {OUT}")

# Verify
d = pymupdf.open(OUT)
total_w = 0
for p_idx, page in enumerate(d):
    for w in page.widgets():
        total_w += 1
        r = w.rect
        if r is not None:
            print(f"  {w.field_name}: page {p_idx + 1}, ({r.x0:.0f},{r.y0:.0f})")
print(f"Total Widgets: {total_w}")
d.close()
