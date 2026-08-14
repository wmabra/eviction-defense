#!/usr/bin/env python3
"""
Create a fillable Kentucky Answer form (Forcible Detainer).

Kentucky has no statewide tenant answer form — forcible detainer is
hearing-based (KRS 383.200-383.275). This recreates the court-accepted
"Answer to Forcible Detainer Complaint" structure as a fillable PDF.
"""
import fitz

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
text(72, 78, "DISTRICT COURT", 11)
lead = fitz.get_text_length("COUNTY, KENTUCKY — ", fontname="helv", fontsize=11)
text(72, 96, "COUNTY, KENTUCKY — ")
field("county", 72 + lead, 84, 140, 16, 10)
text(72, 116, "CASE NO.", 10)
field("case_number", 120, 108, 180, 16, 10)

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
text(72, 555, "DATED: _______________________", 10.5)
field("date", 150, 542, 120, 18, 10)

text(72, 600, "______________________________________", 10.5)
field("signature", 72, 586, 250, 18, 10)
text(72, 620, "Defendant's Signature", 9)

field("printed_name", 72, 640, 250, 18, 10)
text(72, 660, "Printed Name", 9)

field("property_address", 360, 640, 180, 18, 10)
text(360, 660, "Address", 9)

field("phone", 360, 600, 180, 18, 10)
text(360, 620, "Phone", 9)

# ── Certificate of Service ───────────────────────────────
text(72, 710, "CERTIFICATE OF SERVICE", 11, bold=True)
text(72, 730, "I certify that a copy of this Answer was served on the Plaintiff or Plaintiff's", 9.5)
text(84, 746, "attorney on the date above.", 9.5)

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
