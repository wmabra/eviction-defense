"""Reusable editable PDF form-field flowables for reportlab documents.

These flowables render real AcroForm fields (text fields and checkboxes), so the
output PDF is editable by the user in any PDF viewer (Acrobat, Preview, etc.).
This is what lets a tenant open their packet, verify every value, and correct
anything before printing/signing/filing.
"""
from reportlab.platypus import Flowable

from typing import Any, cast

import os

import pymupdf as fitz


# Text that marks a line as part of a signature / attestation / service block.
# Those lines stay ink — the tenant or officer signs and dates them by hand,
# which is the same rule _make_signature_fields_readonly enforces on court forms.
_INK_LINE_MARKERS = (
    "day of", "respectfully submitted", "served by", "subscribed",
    "notary", "signature", "sworn", "affiant", "witness",
)


def make_document_editable(src_path: str, dst_path: str | None = None) -> int:
    """Add editable text fields over every underscore blank in a PDF.

    Returns the number of text fields added.

    Two kinds of underscore run are deliberately NOT turned into fields:

    * a line made up of nothing but underscores is a decorative divider, not an
      input — the generated documents use an 80-underscore rule as a section
      break;
    * a signature / attestation / service-date line ("this ___ day of ___,
      20__") stays ink so it can be signed and dated by hand.

    Runs that sit inside a sentence and are not signature-related ARE genuine
    blanks ("scheduled for ___ at ___ (time)", "approximately ___ days").
    """
    doc = fitz.open(src_path)
    added = 0
    for pno in range(doc.page_count):
        page = doc[pno]
        raw = cast(dict, page.get_text("rawdict"))
        runs = []
        for block in raw.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                # The line's own text decides whether an underscore run on it is
                # an input at all. See the docstring: dividers and signature /
                # service-date lines are not inputs.
                line_text = "".join(
                    str(ch.get("c", ""))
                    for sp in line.get("spans", [])
                    for ch in sp.get("chars", [])
                )
                _stripped = line_text.strip()
                if _stripped and all(c in "_ \t" for c in _stripped):
                    continue                      # decorative divider
                if any(k in line_text.lower() for k in _INK_LINE_MARKERS):
                    continue                      # signature / service-date line
                for span in line.get("spans", []):
                    # A malformed /size can be non-numeric or absurd on damaged
                    # PDFs; a packet must not die over a font-size lookup.
                    try:
                        size = float(span.get("size") or 10.0)
                    except (TypeError, ValueError):
                        size = 10.0
                    if not (4.0 <= size <= 72.0):
                        size = 10.0
                    cur = []
                    for ch in span.get("chars", []):
                        if ch["c"] == "_":
                            cur.append(ch["bbox"])
                        else:
                            if cur:
                                runs.append((cur, size)); cur = []
                    if cur:
                        runs.append((cur, size))
        for r, size in runs:
            if len(r) < 3:
                continue
            x0 = min(b[0] for b in r); y0 = min(b[1] for b in r)
            x1 = max(b[2] for b in r); y1 = max(b[3] for b in r)
            w = cast(Any, fitz.Widget())
            w.field_name = f"fill_{pno}_{added}"
            w.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
            # Size the field to its own text line. The previous fixed 44pt box
            # (y1-42) reached ~3 lines above the underscore and covered the
            # printed line above it on every generated document.
            _h = max(12.0, min(28.0, size * 1.35 + 2.0))
            w.rect = fitz.Rect(x0, y1 - _h, max(x1, x0 + 48), y1 + 2)
            w.field_value = ""
            w.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
            page.add_widget(w)
            added += 1

    # Format existing flowable/native widgets for clean layout alignment:
    for page in doc:
        for w in page.widgets():
            fn = str(w.field_name or "")
            val = str(w.field_value or "").strip()
            # Status badges in table cells (Yes/No): center
            if val in ("Yes", "No"):
                try:
                    doc.xref_set_key(w.xref, "Q", "1")
                    w.update()
                except Exception:
                    pass
            # Case numbers, dates, currency amounts, numbers & household counts: center
            elif any(k in fn.lower() for k in (
                "case_number", "case_no", "caseno", "date", "sig_date",
                "hh_adults", "hh_children", "household_adults", "household_children", "household_size",
                "income_", "expense_", "asset_", "payment_plan_amount", "rent_amount", "amount_claimed",
                "bk_chapter", "bk_case", "continuance_days", "stay_eviction_days", "stay_writ_days",
                "division", "hearing_time", "hearing_date"
            )):
                try:
                    doc.xref_set_key(w.xref, "Q", "1")
                    w.update()
                except Exception:
                    pass

    out = dst_path or src_path
    if out == src_path:
        tmp = src_path + ".tmp"
        doc.save(tmp, deflate=True)
        doc.close()
        os.replace(tmp, src_path)
    else:
        doc.save(out, deflate=True)
        doc.close()
    return added


class FillableText(Flowable):
    """A reportlab flowable that renders an editable PDF text field.

    Args:
        name: unique field name (used to identify the field in the PDF).
        value: initial value (str or None). Empty string = blank editable field.
        width: field width in points.
        height: field height in points.
        font_size: font size for the field text.
    """

    def __init__(self, name: str, value="", width: float = 140, height: float = 18,
                 font_size: float = 10):
        super().__init__()
        self.name = name
        self.value = "" if value is None else str(value)
        # reportlab's AcroForm escapePDF chokes on some unicode punctuation
        for _a, _b in (("\u2014", "-"), ("\u2013", "-"), ("\u2018", "'"), ("\u2019", "'"), ("\u201c", '"'), ("\u201d", '"'), ("\u2026", "...")):
            self.value = self.value.replace(_a, _b)
        self._width = width
        self._height = height
        self.font_size = font_size

    def wrap(self, aW, aH):
        return (self._width, self._height)

    def draw(self):
        c = self.canv
        ax, ay = c.absolutePosition(0, 0)
        c.acroForm.textfield(
            value=self.value,
            name=self.name,
            x=round(ax),
            y=round(ay),
            width=round(self._width),
            height=round(self._height),
            fontName="Helvetica",
            fontSize=self.font_size,
            fieldFlags="multiline",
            maxlen=0,  # 0 removes ReportLab's default 100-character cap
        )


class FillableCheckbox(Flowable):
    """A reportlab flowable that renders an editable PDF checkbox field.

    Args:
        name: unique field name.
        checked: initial checked state.
        size: checkbox size in points.
    """

    def __init__(self, name: str, checked: bool = False, size: float = 14):
        super().__init__()
        self.name = name
        self.checked = bool(checked)
        self.size = size

    def wrap(self, aW, aH):
        return (self.size, self.size)

    def draw(self):
        c = self.canv
        ax, ay = c.absolutePosition(0, 0)
        c.acroForm.checkbox(
            checked=self.checked,
            name=self.name,
            x=round(ax),
            y=round(ay),
            size=round(self.size),
        )
