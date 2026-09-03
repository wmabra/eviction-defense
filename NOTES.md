# Internal Notes (developer-facing — not customer-facing)

## [NEXT PHASE — account system] Prevent sharing/reuse of editable PDF forms

**Status:** Not started. Blocked on the customer account (download) system, which is a future phase.

**Requirement:** Add protection so a paying customer cannot share their editable PDF forms with someone else who then reuses them without paying for the service.

**Context:**

- The document packages are now fully editable — every blank and checkbox is a real AcroForm field (see `app/services/form_fields.py` + `app/services/pdf_overlay.py`).
- They must stay editable for the legitimate customer (verify/correct before printing/signing/filing), but should not be freely redistributable/reusable.

**Ideas to evaluate (none decided yet):**

- Per-page watermark: customer name / email / case ID.
- Unique per-order identifier in PDF metadata.
- "Prepared for [Name] on [Date]" stamp on the cover page + each form.
- Authenticated, logged downloads tied to the account.
- Tamper-evident marker or digital signature to detect/redistribute-trace copies.
