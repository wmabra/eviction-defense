#!/usr/bin/env python3
"""
Create a fillable Missouri Answer form (Rent and Possession Complaint).

Missouri has no statewide fillable answer form — the answer is a typed pleading.
This recreates the court-accepted "Answer to Plaintiff's Rent and Possession
Complaint" structure as a fillable PDF with standardized field names so the
existing pdf_overlay.py unified mapping fills it correctly.
"""
import fitz

OUT = "app/templates/counties/mo_eviction_answer.pdf"

doc = fitz.open()
page = doc.new_page(width=612, height=792)  # letter

W = 612
# Helper: insert static text
def text(x, y, s, size: float = 11, bold: bool = False, color=(0, 0, 0)):
    font = "hebo" if bold else "helv"
    page.insert_text(fitz.Point(x, y), s, fontsize=size, fontname=font, color=color)

# Helper: add a text widget
def field(name, x, y, w, h, fontsize: float = 10, multiline=False):
    wd = fitz.Widget()
    wd.field_name = name  # type: ignore[attr-defined]
    wd.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    wd.rect = fitz.Rect(x, y, x + w, y + h)  # type: ignore[attr-defined]
    wd.field_value = ""  # type: ignore[attr-defined]
    wd.text_font = "Helv"  # type: ignore[attr-defined]
    wd.text_fontsize = fontsize  # type: ignore[attr-defined]
    wd.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE if multiline else 0  # type: ignore[attr-defined]
    page.add_widget(wd)

# ── Caption ──────────────────────────────────────────────
# Measure text widths so the county field doesn't overlap
lead = fitz.get_text_length("IN THE CIRCUIT COURT OF ", fontname="helv", fontsize=12)
text(72, 70, "IN THE CIRCUIT COURT OF ", 12)
field("county", 72 + lead, 57, 120, 18, 11)          # county name
ctail = 72 + lead + 120 + 4
text(ctail, 70, "COUNTY, MISSOURI", 12)
text(72, 92, "ASSOCIATE CIRCUIT DIVISION", 11)

# ── Party block ──────────────────────────────────────────
# Plaintiff (landlord) line
field("plaintiff_name", 72, 130, 300, 18, 11)
text(72, 152, "Plaintiff,", 11)
text(400, 132, "Case No.", 10)
field("case_number", 445, 128, 120, 18, 10)

# vs.
text(72, 180, "vs.", 11)

# Defendant (tenant) line
field("defendant_name", 72, 205, 300, 18, 11)
text(72, 227, "Defendant.", 11)
text(400, 207, "Division No.", 10)
field("division", 455, 203, 110, 18, 10)

# ── Title ────────────────────────────────────────────────
text(72, 265, "DEFENDANT'S ANSWER TO PLAINTIFF'S RENT AND POSSESSION COMPLAINT", 11, bold=True)

# ── Body ────────────────────────────────────────────────
text(72, 300, "Defendant, for the answer to Plaintiff's complaint, states as follows:", 11)
text(72, 325, "1.  Defendant denies each and every allegation of Plaintiff's complaint.", 10.5)
text(72, 345, "2.  Defendant affirmatively states the following defenses and reasons the", 10.5)
text(84, 362, "complaint should be dismissed:", 10.5)

# Large narrative field for defenses
field("defense_narrative", 72, 375, 468, 120, 10, multiline=True)

# ── Signature block ──────────────────────────────────────
text(72, 545, "DATED: _______________________", 10.5)
field("date", 150, 532, 120, 18, 10)

text(72, 590, "______________________________________", 10.5)
field("signature", 72, 576, 250, 18, 10)
text(72, 610, "Defendant's Signature", 9)

field("printed_name", 72, 630, 250, 18, 10)
text(72, 650, "Printed Name", 9)

field("property_address", 360, 630, 180, 18, 10)
text(360, 650, "Address", 9)

field("phone", 360, 590, 180, 18, 10)
text(360, 610, "Phone", 9)

# ── Certificate of Service ───────────────────────────────
text(72, 700, "CERTIFICATE OF SERVICE", 11, bold=True)
text(72, 720, "I certify that a copy of this Answer was served on the Plaintiff or Plaintiff's", 9.5)
text(84, 736, "attorney on the date above.", 9.5)

doc.save(OUT, deflate=True)
doc.close()
print(f"Created fillable form: {OUT}")

# Verify
d = fitz.open(OUT)
widgets = list(d[0].widgets())
print(f"Widgets: {len(widgets)}")
for w in widgets:
    r = w.rect  # type: ignore[attr-defined]
    if r is not None:
        print(f"  {w.field_name}: rect=({r.x0:.0f},{r.y0:.0f},{r.x1:.0f},{r.y1:.0f})")  # type: ignore[attr-defined]
d.close()
