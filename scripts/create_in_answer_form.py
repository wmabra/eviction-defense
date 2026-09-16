#!/usr/bin/env python3
"""
Create a fillable Indiana Answer form (Notice of Claim / Eviction).

Indiana small-claims eviction is hearing-based. This recreates the
court-accepted "Answer to Notice of Claim" structure as a fillable PDF,
including the court caption and a Trial Rule 5(D)-compliant Certificate
of Service.
"""
import pymupdf as fitz

OUT = "app/templates/counties/in_eviction_answer.pdf"

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


# ── Header & Court Name ─────────────────────────────────
text(72, 50, "STATE OF INDIANA", 12, bold=True)
text(72, 66, "COUNTY OF", 11)
lead = fitz.get_text_length("COUNTY OF ", fontname="helv", fontsize=11)
field("county", 72 + lead, 58, 140, 15, 10)

text(300, 50, "IN THE", 11)
field("court_name", 340, 42, 200, 15, 10)
text(300, 66, "DIVISION:", 11)
field("division", 355, 58, 185, 15, 10)

text(72, 96, "CASE NO.", 10)
field("case_number", 125, 88, 180, 15, 10)

# ── Party block ──────────────────────────────────────────
field("plaintiff_name", 72, 130, 280, 18, 11)
text(72, 152, "Plaintiff / Landlord,", 10)

text(72, 180, "v.", 11)

field("defendant_name", 72, 200, 280, 18, 11)
text(72, 222, "Defendant / Tenant.", 10)

# ── Title ────────────────────────────────────────────────
text(72, 285, "ANSWER TO NOTICE OF CLAIM (EVICTION)", 11, bold=True)

# ── Body ────────────────────────────────────────────────
text(72, 320, "Defendant, for the answer to Plaintiff's Notice of Claim, states as follows:", 11)
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

# ── Certificate of Service (Ind. Tr. R. 5(D)) ───────────
text(72, 692, "CERTIFICATE OF SERVICE", 11, bold=True)
text(72, 708, "I certify that on the date above, a true and correct copy of this Answer was served", 9.5)
text(72, 722, "upon the Plaintiff or Plaintiff's attorney of record by:  [ ] U.S. Mail  [ ] Hand Delivery  [ ] IEFS / Email", 9.5)
text(72, 742, "Served to: ____________________________________________________________________", 9.5)
text(72, 764, "______________________________________", 10)
text(72, 778, "Signature of Person Serving", 8.5)

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
