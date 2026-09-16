# Project State — evictions.help (eviction-defense)

> Handoff doc for resuming work across sessions. **Read this file first.**

## What this is

evictions.help is a self-help eviction-defense document preparation service (flat fee $299).
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

## State-by-state review progress (developer QA)

We're doing a state-by-state QA pass: generate a "John Doe" test packet, read the
developer's Google-Doc review comments for that state, fix every flagged issue, commit.

**Round 1 — fixed + committed (11 states, alphabetical):**
`AR · CO · CO_Denver · CT · GA · IL · IN · KY · LA · MI · MN`

**Round 2 — recheck with developer (in progress):**

- ✅ **AR** — regenerated fresh (commit `585618d`): 0 overlaps, Yes/No pairs
  single-selected.
- ✅ **CO + CO_Denver** — regenerated (commit `5a16f6a`): 0 overlaps.
- ✅ **CT** — regenerated (commit `5a16f6a`): Yes/No single-selected; 12 overlaps are
  the accepted white-fill pattern (financial `$` values + court caption).
- ✅ **GA** — regenerated (commit `577a055`): Yes/No pairs single-selected (income
  sources land on "No" when absent), real-estate asset "Address" no longer gets
  the rental address, plaintiff caption filled, ZapfDingbats re-sanitized, State/Zip
  filled, second vehicle row blank.
- ⏳ Next: **IL**, then IN, KY, LA, MI, MN.

**Not yet started (remaining 10 states):**
`MO · NM · OH · OK · OR · RI · SC · TN · TX · VA`

### Key cross-cutting fixes landed in this pass

- Document-wide field detection (widgets summed across all pages) — stops multi-page
  answer forms (LA 14-page) being misflagged as non-fillable.
- Hybrid overlay: run coordinate overlay on answer forms that have fillable checkboxes
  but no caption widgets (LA caption).
- Removed legacy `_flip()` in `_make_scanned_form_editable()` — auto-detected
  checkboxes/blanks were being placed upside down on scanned forms.
- Cover-page manifest renumbered so Document N matches each file; court Answer + Fee
  Waiver are Documents 1–2, supporting docs 03+.
- Motion date declarations now dynamic (`f"…this {d.day} day of {d.strftime('%B')}, {d.year}."`)
  instead of static `_____ day of __________, 20____`.
- State-specific writ terminology in cover page + stay-writ motion (MI "Order of
  Eviction", MN "Writ of Recovery") and LA caption "Court COURT" dedupe.
- YES/NO checkbox exclusivity: fee-waiver Yes/No pairs now check exactly one box
  (decided by proximity to the printed Yes/No labels — `on_state` proved unreliable
  because some templates give every box the same on-state) and explicitly deselect
  the other half; "employed" no longer falls back to gross income.
- Income-source Yes/No rows (workers comp, insurance, pension, child support,
  alimony, social security, unemployment) map to specific financial keys and check
  "No" when absent, instead of false-matching `work` → `workers` → employment.
- Checkbox keyword matching now restricted to the checkbox's own row (the ±8pt
  band) so an adjacent row's label can't leak into the question text.
- ZapfDingbats `/WinAnsiEncoding` sanitize now runs BOTH on the source template and
  again right before save (PyMuPDF re-adds the bad encoding when it generates
  checkbox appearance streams during `widget.update()`).
- Repeated-row guard: substring auto-fill no longer copies one row's value into a
  sibling (`…value of the vehicle` vs `…value of the vehicle_2`).
- PyMuPDF deprecation migration: `import fitz` → `import pymupdf as fitz` across 16
  files (drop-in alias; `fitz.Rect/open/Widget` are the same objects as `pymupdf.*`).
- New `defense_details` config (per-item explanation text) + `explanation_*` overlay
  routing (MN HOU202 items 5/6/9); corrected MI DC 111a defense→item mapping.

## Current state (fully working)

1. **Every form is editable.** Every blank and every checkbox across all 20 states is an
   editable PDF field — verified **0 gaps**. Only signature/notary lines stay as ink.
   **Text-over-text overlap: 0 across all 20 states (answer + fee waiver)** — guarded by
   `tests/check_all_overlap.py` (OCR-based) and `tests/verify_editable_fields.py`
   (420 forms, 0 failures).
2. **Removed-state cleanup done.** CA / AZ / FL / NV / MA (plus never-covered MS / NC)
   references and documents were removed from the project.
3. **Intake agents instruct the user** (chat + voice) to download, verify on a computer,
   edit any mistakes, then print / sign / file.
4. **Internal note:** anti-sharing/reuse protection is required for the account phase
   (see `NOTES.md`).
5. **Admin test-packet endpoint:** `POST /api/v1/admin/generate-test-packet` lets
   Mark/William generate any packet on demand (password-gated, unlimited, no customer
   account) — returns the zip from arbitrary data with sensible defaults.

## How the editable-field system works

- `FillableText` / `FillableCheckbox` flowables (reportlab AcroForm) → generated docs.
- `make_document_editable()` post-processor → converts underscore blanks to text fields.
- `pdf_overlay._make_scanned_form_editable()` → auto-detects **every** blank/checkbox
  (underscores, horizontal lines, rectangle boxes, `☐` glyphs, vector squares) and adds
  editable widgets on **all** court forms (fillable + scanned).

## Next steps / future work

1. **Customer account + download system** (next phase) — see `NOTES.md` for anti-sharing requirement.
2. **Secure the admin panel** — `app/routers/admin.py` endpoints `/stats`, `/cases`, `/cases/{id}`,
   `/cases/{id}/resend`, and `/chat-sessions` are NOT yet password-gated (only the new
   `generate-test-packet` endpoint is). Add the admin-password/token check to all of them.
3. Deploy/publish the SEO city/county pages (scripts in `scripts/`).
4. (Optional) refine pre-fill field-name matching on the scanned fee-waiver forms.

## How to resume quickly

Just say: *"let's work on the eviction-defense project"* and point me at this file
(`~/eviction-defense/PROJECT_STATE.md`). I'll read it and continue from here.

## Deployment (production server — evictions.help)

- **Server:** Digital Ocean droplet `167.172.139.63` (hostname `eviction-defense`). SSH: `ssh root@167.172.139.63`.
- **App dir:** `/opt/eviction-defense` (owned by `deploy` user). Git remote = `https://github.com/wmabra/eviction-defense.git`.
- **Run by:** systemd `eviction-defense.service` → `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2` (user `deploy`, env from `/opt/eviction-defense/.env`), fronted by nginx.
- **Deploy steps:**
  1. `cd /opt/eviction-defense && sudo -u deploy git pull origin main`  (or run git as root + `chown -R deploy:deploy`)
  2. `sudo systemctl restart eviction-defense`
  3. Verify: `curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8000/`
- **Backups:** `/opt/backups/` (weekly SQL + pre-deploy tarballs).
- **Note:** startup occasionally races `create_all()` across the 2 workers ("table users already exists") and self-heals on the next restart — consider a migration/`checkfirst` fix later.
