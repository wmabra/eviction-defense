# Denver, CO — End-to-End User QA Findings

**Date:** 2026-09-24
**Tester:** QA (simulated end-user "Marcus Anthony Rivera", City & County of Denver)
**Code under test:** `main` @ `4c2c39c` (pulled before testing — includes the developer's
latest commits, including "combine bank accounts in fee waiver").

## What was exercised

Full production flow, driven against a local instance (`uvicorn app.main:app`):

1. **Eligibility pre-screen** (`POST /api/v1/intake/pre-screen`) — passed.
2. **Chat intake** (`POST /api/v1/chat/send`, live DeepSeek agent) — all 6 phases,
   ~40 turns, answered as a realistic Denver tenant.
3. **Packet generation** (`POST /api/v1/documents/generate-packet`) — 16-document ZIP.

## Artifacts

- ZIP: `~/Downloads/eviction-defense-qa/denver/denver_packet_v2.zip`
- Unzipped PDFs: `~/Downloads/eviction-defense-qa/denver/unzipped/`
- Structured intake data: `~/Downloads/eviction-defense-qa/denver/chat_extracted.json`
- Full chat transcript: `~/Downloads/eviction-defense-qa/denver/chat_history.json`

## 🔴 Critical — Denver narrative defense is dropped (still broken)

The Denver answer form (**DCC CP No. 3**, `co_denver_answer.pdf`) is generated with
generic boilerplate instead of the tenant's actual story.

Filled `defense_narrative` field on the answer form:

> The defendant requests that the court deny the eviction and allow the defendant to
> remain in possession of the premises.

The tenant's real narrative — broken furnace/water heater, disputed amount
($1,925 vs $3,850), pending rental assistance — **does not appear anywhere on the form**.
For a narrative answer, this makes the document effectively useless: the court receives
no substantive reasons.

### Root cause

The chat agent collects Denver's free-form defense under a `narrative` key:

```json
"defenses": { "narrative": { "checked": true, "explanation": "I should not be evicted because ..." } }
```

But the generator only understands checkbox defense keys:

- `app/services/chat.py` — `_defense_list_for_state()` returns
  `NARRATIVE_DEFENSE_INSTRUCTION` for `CO` + `Denver` (line ~260), so the agent
  asks "What is your side of the story?" and emits a free-form `narrative` entry.
- `app/services/pdf_overlay.py` — `_build_defense_narrative()` (line ~2427) iterates a
  `DEFENSE_LABELS` map of only `def_*` keys. There is **no `"narrative"` key**, so no
  entry matches, `checked` stays empty, and it returns the fallback boilerplate.

This is **Denver-specific**: the other narrative states (AR, NM, TN, MO, KY, OK, IN, OH)
collect `def_*` checkboxes, so `_build_defense_narrative()` produces correct text for them.

### Suggested fix

Either:
1. In `_build_defense_narrative()`, first check for a `defenses.get("narrative")` (or a
   free-text key) and return its `explanation` verbatim; or
2. Have the Denver intake emit standard `def_*` keys (parsed from the narrative) so the
   existing builder path is reused. Option 1 is lower-risk and preserves the user's
   exact wording.

## 🟢 Confirmed fixed in the developer's recent commits

- **Phone truncation** — answer form now shows `(720) 555-0132` (was clipped to `(720)`).
- **Fee-waiver auto-qualification** — `receives_snap` is correctly detected → Section 6
  set to "Yes" + SNAP checked (field `6.5`) → Sections 7–10 correctly left blank per the
  JDF 205 instructions ("Skip to Section 11") → signature block filled.
- **Hearing mode / trial type** — `checkbox_hearing_in_person` and
  `checkbox_trial_to_court` correctly checked.

## 🟢 Working correctly

- Cover page, hardship letter, payment-plan letter ($300), motion for continuance (with
  the specific reason "give rental assistance application time to be approved"),
  certificate of service, and all 16 documents.
- Court answer form: plaintiff, defendant, address, case number, phone, email, CoS.
- Fee waiver: name, address, case number, county, phone, email, SNAP, signature.

## 🟡 Minor gaps

1. **DOB collected but dropped.** `SYSTEM_PROMPT` Phase 1 says date of birth is
   *"REQUIRED for fee waiver and court identification"* and the agent asks for it, but:
   - `PersonalInfo` in `app/schema/intake.py` has no `date_of_birth` field;
   - the agent omits it from `extracted_data`;
   - the JDF 205 "Date of Birth" field is left blank.
2. **Fee-waiver Section 9 totals** show `0` / `0` when the tenant auto-qualifies via SNAP
   (cosmetic — arguably should be blank when skipping sections 7–10).
3. **Motion for continuance** renders both a generic template reason ("personal or family
   circumstances…") *and* the tenant's specific reason — possible duplication.
