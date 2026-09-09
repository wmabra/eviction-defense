"""Reusable editable PDF form-field flowables for reportlab documents.

These flowables render real AcroForm fields (text fields and checkboxes), so the
output PDF is editable by the user in any PDF viewer (Acrobat, Preview, etc.).
This is what lets a tenant open their packet, verify every value, and correct
anything before printing/signing/filing.
"""
from reportlab.platypus import Flowable

from typing import Any, cast

import os

import fitz


def make_document_editable(src_path: str, dst_path: str | None = None) -> int:
    """Add editable text fields over every underscore blank in a PDF.

    Returns the number of text fields added. Signature *lines* (drawn rules,
    not underscores) are left alone so the user can sign with ink.
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
                for span in line.get("spans", []):
                    cur = []
                    for ch in span.get("chars", []):
                        if ch["c"] == "_":
                            cur.append(ch["bbox"])
                        else:
                            if cur:
                                runs.append(cur); cur = []
                    if cur:
                        runs.append(cur)
        for r in runs:
            if len(r) < 3:
                continue
            x0 = min(b[0] for b in r); y0 = min(b[1] for b in r)
            x1 = max(b[2] for b in r); y1 = max(b[3] for b in r)
            w = cast(Any, fitz.Widget())
            w.field_name = f"fill_{pno}_{added}"
            w.field_type = fitz.PDF_WIDGET_TYPE_TEXT  # type: ignore[attr-defined]
            w.rect = fitz.Rect(x0, y1 - 42, max(x1, x0 + 48), y1 + 2)
            w.field_value = ""
            w.field_flags = fitz.PDF_TX_FIELD_IS_MULTILINE  # type: ignore[attr-defined]
            page.add_widget(w)
            added += 1
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
