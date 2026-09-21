# Project State — evictions.help (eviction-defense)

> Handoff doc for resuming work across sessions. **Read this file first.**

## What this is

evictions.help is a self-help eviction-defense document preparation service (flat fee $299).
Flow: **eligibility → payment ($299) → email verification → account (username = verified email + temp password) → chat intake agent (resumable) → pre-filled editable PDF packet → user verifies/edits → downloads ZIP from their account → prints/signs/files at court.**

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
  - `app/services/voice_prompt.md` — phone/voice agent prompt (Retell "Eva")
  - `app/services/eligibility.py` — 20-state + county eligibility
  - `app/routers/auth.py` — login / me / change-password / forgot-password / verify-email / resend-verification
  - `app/routers/voice.py` — voice-agent tool endpoints (`/api/v1/voice/*`)
  - `scripts/deploy_voice_agent.py` — pushes the prompt + tools to Retell
  - `scripts/import_telnyx_number.py` — imports the Telnyx number into Retell
  - `docs/voice-agent.md` — full voice-agent setup + ops reference

## State-by-state review progress (developer QA)

We're doing a state-by-state QA pass: generate a "John Doe" test packet, read the
developer's Google-Doc review comments for that state, fix every flagged issue, commit.

**Round 1 — fixed + committed (11 states, alphabetical):**
`AR · CO · CO_Denver · CT · GA · IL · IN · KY · LA · MI · MN`

**Round 2 — recheck with developer (complete):**

- ✅ **AR** — regenerated fresh (commit `585618d`): 0 overlaps, Yes/No pairs
  single-selected.
- ✅ **CO + CO_Denver** — regenerated (commit `5a16f6a`): 0 overlaps.
- ✅ **CT** — regenerated (commit `5a16f6a`): Yes/No single-selected; 12 overlaps are
  the accepted white-fill pattern (financial `$` values + court caption).
- ✅ **GA** — regenerated (commit `577a055`): Yes/No pairs single-selected (income
  sources land on "No" when absent), real-estate asset "Address" no longer gets
  the rental address, plaintiff caption filled, ZapfDingbats re-sanitized, State/Zip
  filled, second vehicle row blank.
- ✅ **IL** — regenerated (commit `ae315a9`): all 6 dev issues confirmed fixed
  (Circuit Court fee-waiver template, 1a General Denial, no phantom dates, page-4
  certification, proof-of-delivery → landlord, caption not triplicated); fixed the
  paragraph-triad radio multi-select and remapped affirmative defenses to their
  correct 2a–2g checkboxes.
- ✅ **IN** — regenerated (commit `5d370ce`): inverted parties (tenant=Petitioner),
  no `$ $`, case number on the page-3 Order, court header + Trial Rule 5(D)
  Certificate of Service added to the rebuilt answer form, stale continuance date
  blanked, payment-plan start date → next month, orphaned page breaks fixed.
- ✅ **KY** — regenerated (commit `c2dde85`): fee-waiver AOC-026 mapping, rent/mortgage
  checkbox detection, CR 5.03 CoS, phone split, and warrant-for-possession
  terminology (motion title, cover page, and filename) all confirmed/fixed.
- ✅ **LA** — regenerated (commit `7d41906`): all 5 dev issues confirmed fixed
  (document-wide field detection, hybrid overlay on the 14-page answer, caption
  geometry, fee-waiver mappings with no `$ $`/boolean-into-dollar/phone-into-utility,
  Mover/Order names filled, no `Court COURT`).
- ✅ **MI** — regenerated (commit `a2ed72a`): DC 111a defense→item mapping +
  details/Item-11 narratives, MC 20 caption/benefit checkboxes (fixed an `ssi`
  substring false-match on "assistance" fields via word-boundary matching),
  household size, income frequency, and "Order of Eviction" terminology.
- ✅ **MN** — regenerated (commit `86d8204`): `_flip` removal, FEE102 caption/verification,
  cover page, dynamic dates + "Writ of Recovery", and added the HOU202 defense
  checkboxes (Q5/Q6/Q9/Q10).

**Round 2 complete for the 11 states (AR–MN).** Additional developer rechecks followed
(docs NEW18–NEW24) covering CT, GA, IN, KY, LA, MI, CO, MN, IL, and AR — all fixed and
committed. The developer's latest layout pass (field centering, single-page income
worksheet, refined court captions) is also merged.

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
   **Text-over-text overlap: 0 across the 12 reviewed states (AR–MN + CO-Denver)** — guarded by
   `tests/check_all_overlap.py` (OCR-based) and `tests/verify_editable_fields.py`
   (419 forms, 0 failures). The 8 not-yet-reviewed states past MN (MO, NM, OH, OK, OR, RI,
   TN, TX) have caption overlaps from the latest layout pass and will be cleaned up when
   we reach them.
2. **Removed-state cleanup done.** CA / AZ / FL / NV / MA (plus never-covered MS / NC)
   references and documents were removed from the project.
3. **Intake agents instruct the user** (chat + voice) to download, verify on a computer,
   edit any mistakes, then print / sign / file.
4. **Internal note:** anti-sharing/reuse protection is required for the account phase
   (see `NOTES.md`).
5. **Admin test-packet endpoint:** `POST /api/v1/admin/generate-test-packet` lets
   Mark/William generate any packet on demand (password-gated, unlimited, no customer
   account) — returns the zip from arbitrary data with sensible defaults.
6. **Phone voice agent ("Eva")** — live on `+1-561-960-0485` via Retell AI + Telnyx SIP.
   Full prompt (compliance, legal-boundary, off-topic redirect, same-day-callback flow),
   8 tools wired to `/api/v1/voice/*`, post-call analysis, call persistence (`call_logs`),
   and callback email to <support@evictions.help>. See `docs/voice-agent.md`.
7. **Customer accounts** — email-verified signup: payment creates the case in
   `pending_email_verification`, a signed 48h link verifies the email, then the account
   (username = email + temp password) is created and the welcome email sent. Login →
   dashboard (progress bar) → resumable intake → ZIP download. Password change +
   forgot/reset are wired.
8. **Intake resume + granular progress** — the chat session (phase + collected data)
   persists to `case.chat_session`, and the agent emits a `{"phase_completed": N}` marker
   after each phase so the dashboard progress bar advances 25% → 55% through intake, then
   100% at packet-ready.

## How the editable-field system works

- `FillableText` / `FillableCheckbox` flowables (reportlab AcroForm) → generated docs.
- `make_document_editable()` post-processor → converts underscore blanks to text fields.
- `pdf_overlay._make_scanned_form_editable()` → auto-detects **every** blank/checkbox
  (underscores, horizontal lines, rectangle boxes, `☐` glyphs, vector squares) and adds
  editable widgets on **all** court forms (fillable + scanned).

## Next steps / future work

1. **Remaining 10 states** (MO, NM, OH, OK, OR, RI, SC, TN, TX, VA) — QA each state
   against the developer's notes (same flow as AR–MN), including the caption-overlap
   cleanups from the latest layout pass.
2. **Anti-sharing/reuse protection** for the account download (see `NOTES.md`).
3. **Secure the admin panel** — `app/routers/admin.py` endpoints `/stats`, `/cases`,
   `/cases/{id}`, `/cases/{id}/resend`, and `/chat-sessions` are NOT yet password-gated
   (only the `generate-test-packet` endpoint is). Add the admin-password/token check.
4. Deploy/publish the SEO city/county pages (scripts in `scripts/`).

## How to resume quickly

Just say: *"let's work on the eviction-defense project"* and point me at this file
(`~/eviction-defense/PROJECT_STATE.md`). I'll read it and continue from here.

## Deployment (production server — evictions.help)

- **Server:** Digital Ocean droplet `167.172.139.63` (hostname `eviction-defense`). SSH: `ssh root@167.172.139.63`.
- **App dir:** `/opt/eviction-defense` (owned by `deploy` user). Git remote = `https://github.com/wmabra/eviction-defense.git`.
- **Run by:** systemd `eviction-defense.service` → `uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2` (user `deploy`, env from `/opt/eviction-defense/.env`), fronted by nginx.
- **Deploy (manual — verify FIRST, then trigger; never auto-deploy):**
  1. Verify locally: `venv/bin/python -m pytest -q` (expect 34 passed), `venv/bin/python tests/check_all_overlap.py` (0 overlaps), `venv/bin/python tests/verify_editable_fields.py` (0 failures). Deploy only if all green.
  2. Commit + push to `main`. Pushing does NOT auto-deploy.
  3. Trigger: `gh workflow run deploy.yml` (or GitHub → Actions → "Deploy to production" → Run workflow). The workflow SSHs in, `git pull`s as `deploy`, restarts the service, and health-checks.
- **Manual fallback:** `ssh root@167.172.139.63 'cd /opt/eviction-defense && sudo -u deploy git pull origin main && systemctl restart eviction-defense'`
- **GitHub Actions secrets:** `DEPLOY_SSH_KEY`, `DEPLOY_HOST`, `DEPLOY_USER`.
- **Backups:** `/opt/backups/` (weekly SQL + pre-deploy tarballs).
- **Note:** startup occasionally races `create_all()` across the 2 workers ("table users already exists") and self-heals on the next restart — consider a migration/`checkfirst` fix later.
