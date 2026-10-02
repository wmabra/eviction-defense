#!/usr/bin/env python3
"""
Create a fillable Kentucky Answer form (Forcible Detainer).

Kentucky has no statewide tenant answer form — forcible detainer is
hearing-based (KRS 383.200-383.275). This recreates the court-accepted
"Answer to Forcible Entry and Detainer Petition" structure as a fillable PDF.
"""
import pymupdf

OUT = "app/templates/counties/ok_eviction_answer.pdf"

doc = pymupdf.open()
page = doc.new_page(width=612, height=792)  # letter


def text(x, y, s, size: float = 11, bold: bool = False):
    font = "hebo" if bold else "helv"
    page.insert_text(pymupdf.Point(x, y), s, fontsize=size, fontname=font)


def field(name, x, y, w, h, fontsize: float = 10, multiline=False):
    wd = pymupdf.Widget()
    wd.field_name = name  # type: ignore[attr-defined]
    wd.field_type = pymupdf.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
    wd.rect = pymupdf.Rect(x, y, x + w, y + h)  # type: ignore[attr-defined]
    wd.field_value = ""  # type: ignore[attr-defined]
    wd.text_font = "Helv"  # type: ignore[attr-defined]
    wd.text_fontsize = fontsize  # type: ignore[attr-defined]
    wd.field_flags = pymupdf.PDF_TX_FIELD_IS_MULTILINE if multiline else 0  # type: ignore[attr-defined]
    page.add_widget(wd)


# ── Caption ──────────────────────────────────────────────
text(72, 55, "IN THE DISTRICT COURT OF", 12)
field("county", 72, 65, 110, 16, 10)
text(188, 77, "COUNTY, STATE OF OKLAHOMA", 11, bold=True)
text(72, 105, "CASE NO.", 10)
field("case_number", 130, 95, 180, 16, 10)

# ── Party block ──────────────────────────────────────────
field("plaintiff_name", 72, 126, 280, 16, 10)
text(72, 154, "Plaintiff,", 10)
text(390, 105, "DIVISION NO.", 10)
field("division", 465, 95, 80, 16, 10)

text(72, 175, "v.", 10)

field("defendant_name", 72, 192, 280, 16, 10)
text(72, 220, "Defendant.", 10)

# ── Title ────────────────────────────────────────────────
text(72, 250, "ANSWER TO FORCIBLE ENTRY AND DETAINER PETITION", 11, bold=True)

# ── Body ────────────────────────────────────────────────
text(72, 280, "Defendant, for the answer to Plaintiff's Forcible Entry and Detainer Petition, states as follows:", 10.5)
text(72, 302, "1.  Defendant denies each and every allegation of Plaintiff's complaint.", 10)
text(72, 320, "2.  Defendant affirmatively states the following defenses and reasons the complaint should be dismissed:", 10)

field("defense_narrative", 72, 335, 468, 180, 10, multiline=True)

# ── Signature block ──────────────────────────────────────
text(72, 545, "DATED: _______________________", 10.5)
field("date", 120, 533, 140, 16, 10)

page.draw_line(pymupdf.Point(72, 600), pymupdf.Point(320, 600))
field("signature", 72, 582, 248, 16, 10)
text(72, 612, "Defendant's Signature", 9)

field("printed_name", 72, 632, 248, 16, 10)
page.draw_line(pymupdf.Point(72, 650), pymupdf.Point(320, 650))
text(72, 662, "Printed Name", 9)

field("phone", 360, 582, 180, 16, 10)
page.draw_line(pymupdf.Point(360, 600), pymupdf.Point(540, 600))
text(360, 612, "Phone", 9)

field("property_address", 360, 632, 180, 16, 8.0)
page.draw_line(pymupdf.Point(360, 650), pymupdf.Point(540, 650))
text(360, 662, "Address", 9)

# ── Certificate of Service ───────────────────────────────
text(72, 700, "CERTIFICATE OF SERVICE", 11, bold=True)
text(72, 720, "I certify that a copy of this Answer was served on the Plaintiff or Plaintiff's attorney on the date above.", 9.5)

doc.save(OUT, deflate=True)
doc.close()
print(f"Created fillable form: {OUT}")

d = pymupdf.open(OUT)
widgets = list(d[0].widgets())
print(f"Widgets: {len(widgets)}")
for w in widgets:
    r = w.rect  # type: ignore[attr-defined]
    if r is not None:
        print(f"  {w.field_name}: rect=({r.x0:.0f},{r.y0:.0f})")  # type: ignore[attr-defined]
d.close()
