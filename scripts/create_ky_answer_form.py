#!/usr/bin/env python3
"""
Create a fillable Kentucky Answer form (Forcible Detainer).

Kentucky has no statewide tenant answer form — forcible detainer is
hearing-based (KRS 383.200-383.275). This recreates the court-accepted
"Answer to Forcible Detainer Complaint" structure as a fillable PDF with a
KY CR 5.03 Certificate of Service.
"""
import pymupdf as fitz

OUT = "app/templates/counties/ky_eviction_answer.pdf"

doc = fitz.open()
page = doc.new_page(width=612, height=792)  # letter


def text(x, y, s, size: float = 11, bold: bool = False):
    font = "hebo" if bold else "helv"
    page.insert_text(fitz.Point(x, y), s, fontsize=size, fontname=font)


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
text(72, 60, "COMMONWEALTH OF KENTUCKY", 12, bold=True)
field("county", 72, 80, 150, 16, 10)
text(235, 82, "DISTRICT COURT", 11)
text(72, 116, "CASE NO.", 10)
field("case_number", 130, 108, 200, 16, 10)

# ── Party block ──────────────────────────────────────────
field("plaintiff_name", 72, 150, 280, 18, 11)
text(72, 172, "Plaintiff,", 11)
text(400, 152, "DIVISION NO.", 10)
field("division", 465, 146, 80, 18, 10)

text(72, 200, "v.", 11)

field("defendant_name", 72, 225, 280, 18, 11)
text(72, 247, "Defendant.", 11)

# ── Title ────────────────────────────────────────────────
text(72, 285, "ANSWER TO FORCIBLE DETAINER COMPLAINT", 11, bold=True)

# ── Body ────────────────────────────────────────────────
text(72, 320, "Defendant, for the answer to Plaintiff's Forcible Detainer Complaint, states as follows:", 11)
text(72, 345, "1.  Defendant denies each and every allegation of Plaintiff's complaint.", 10.5)
text(72, 365, "2.  Defendant affirmatively states the following defenses and reasons the", 10.5)
text(84, 382, "complaint should be dismissed:", 10.5)

field("defense_narrative", 72, 395, 468, 120, 10, multiline=True)

# ── Signature block ──────────────────────────────────────
text(72, 545, "DATED: _______________________", 10.5)
field("date", 150, 532, 120, 18, 10)

field("signature", 72, 570, 250, 18, 10)
text(72, 594, "Defendant's Signature", 9)

field("phone", 360, 570, 180, 18, 10)
text(360, 594, "Phone Number", 9)

field("printed_name", 72, 616, 250, 18, 10)
text(72, 640, "Printed Name", 9)

field("property_address", 360, 616, 180, 18, 10)
text(360, 640, "Street Address, City, State, ZIP", 9)

# ── CR 5.03 Certificate of Service ───────────────────────
text(72, 678, "CERTIFICATE OF SERVICE (KY CR 5.03)", 10, bold=True)
text(72, 694, "I hereby certify that on the date above, a true and correct copy of this Answer was served upon", 9)
text(72, 708, "the Plaintiff or Plaintiff's attorney of record by: [ ] U.S. Mail  [ ] Hand Delivery  [ ] Electronic Service", 9)
text(72, 724, "Served to:", 9)
field("cert_name", 130, 716, 400, 16, 10)
text(72, 752, "______________________________________", 10)

doc.save(OUT, deflate=True)
doc.close()
print(f"Created fillable form: {OUT}")

d = fitz.open(OUT)
widgets = list(d[0].widgets())
print(f"Widgets: {len(widgets)}")
for w in widgets:
    r = w.rect  # type: ignore[attr-defined]
    if r is not None:
        print(f"  {w.field_name}: rect=({r.x0:.0f},{r.y0:.0f})")  # type: ignore[attr-defined]
d.close()
