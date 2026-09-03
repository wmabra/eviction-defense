# Project State — evictions.help (eviction-defense)

> Handoff doc for resuming work across sessions. **Read this file first.**

## What this is

evictions.help is a self-help eviction-defense document preparation service (flat fee $399).
Flow: **eligibility (8 questions) → payment → chat intake agent → pre-filled editable PDF packet → user verifies/edits → prints/signs/files at court.**

## The 20 states we cover

`AR, CO, CT, GA, IL, IN, KY, LA, MI, MN, MO, NM, OH, OK, OR, RI, SC, TN, TX, VA`

## Where things live

- Project: `~/eviction-defense` (FastAPI + SQLite + reportlab + PyMuPDF)
- Per-state blank-form packages (20 zips): `~/Downloads/Blank Forms/`
- Key modules:
  - `app/services/generator.py` — generates the ~16 guide/motion docs
  - `app/services/pdf_overlay.py` — fills court answer + fee-waiver forms
  - `app/services/form_fields.py` — editable AcroForm flowables (`FillableText`/`FillableCheckbox`) + `make_document_editable()`
  - `app/services/state_configs.py` — per-state form configs + overlay positions
  - `app/services/chat.py` — chat intake agent (`SYSTEM_PROMPT`)
  - `app/services/voice_prompt.md` — phone/voice agent prompt
  - `app/services/eligibility.py` — 20-state + county eligibility

## Current state (fully working)

1. **Every form is editable.** Every blank and every checkbox across all 20 states is an
   editable PDF field — verified **0 gaps**. Only signature/notary lines stay as ink.
2. **Removed-state cleanup done.** CA / AZ / FL / NV / MA (plus never-covered MS / NC)
   references and documents were removed from the project.
3. **Intake agents instruct the user** (chat + voice) to download, verify on a computer,
   edit any mistakes, then print / sign / file.
4. **Internal note:** anti-sharing/reuse protection is required for the account phase
   (see `NOTES.md`).

## How the editable-field system works

- `FillableText` / `FillableCheckbox` flowables (reportlab AcroForm) → generated docs.
- `make_document_editable()` post-processor → converts underscore blanks to text fields.
- `pdf_overlay._make_scanned_form_editable()` → auto-detects **every** blank/checkbox
  (underscores, horizontal lines, rectangle boxes, `☐` glyphs, vector squares) and adds
  editable widgets on **all** court forms (fillable + scanned).

## Next steps / future work

1. **Customer account + download system** (next phase) — see `NOTES.md` for anti-sharing requirement.
2. Deploy/publish the SEO city/county pages (scripts in `scripts/`).
3. (Optional) refine pre-fill field-name matching on the scanned fee-waiver forms.

## How to resume quickly

Just say: *"let's work on the eviction-defense project"* and point me at this file
(`~/eviction-defense/PROJECT_STATE.md`). I'll read it and continue from here.
