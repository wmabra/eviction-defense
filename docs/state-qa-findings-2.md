# State-by-State End-to-End User QA — KY, LA, MI, MN, MO

**Date:** 2026-09-24
**Tester:** QA (simulated end-users, full website flow: eligibility → chat intake → packet generation)
**Code under test:** `main` @ `ebf2e7b` (+ local QA commits)

Five states driven through the **real chat intake** (live DeepSeek agent, ~45 turns each),
exactly as a website user would.

| State | County | Persona | Docs | Verdict |
|-------|--------|---------|------|---------|
| KY | Jefferson | Amara Whitfield (Louisville) | 18 | ✅ works |
| LA | Orleans | Jerome Boudreaux (New Orleans) | 16 | ✅ works (1 minor gap) |
| MI | Wayne | Keisha Washington (Detroit) | 18 | ✅ works |
| MN | Hennepin | Erik Lindberg (Minneapolis) | 18 | 🔴 fee waiver broken |
| MO | St. Louis County | Cynthia Hayes | 18 | ✅ works |

## Artifacts

```
~/Downloads/eviction-defense-qa/<STATE>/
├── packet.zip          # generated ZIP
├── unzipped/           # all PDFs
├── chat_extracted.json # structured intake data
└── chat_history.json   # (full transcript in /tmp/chat_cases/<STATE>/history.json)
```

## ✅ Confirmed working

- **Full flow** — eligibility pre-screen passed, 6-phase chat completed, packet generated
  with no server errors, for all 5 states.
- **Answer forms** — tenant name, case number, landlord, address, phone, email, CoS all
  correct on every state's form.
- **Defenses map correctly**:
  - KY narrative (`defense_narrative` built from `def_*`) ✓
  - MO narrative (`defense_narrative`) ✓
  - MI DC 111a agree/disagree — `def_amount` → "disagree 5" + details, `def_repairs` →
    "disagree 7" + details ✓
  - LA 14-page checkbox answer — `def_no_written_notice` / `def_accepted_rent` /
    `def_too_vague` mapped ✓
  - MN HOU202 scanned overlay — `def_repairs`/`def_amount`/`def_bad_notice` checkboxes +
    explanation lines ✓
- **Fee waiver filled correctly** in KY (income + assets/debts), LA (income + full
  expense/asset table), MI (income + SNAP/Medicaid), and MO (income + full expense/asset
  table). MO with **Medicaid-only** does **not** misfire the way IL does — it fills the
  financial path correctly.

## 🔴 Critical — Minnesota fee waiver is broken (MN/Hennepin)

Erik (no public benefits) gets a fee waiver that is **not usable as-is**:

1. **No financial data.** The `fee_waiver_overlay` for `mn_fee_waiver.pdf`
   (`app/services/state_configs.py`, MN block) maps only caption/signature fields
   (county, case number, name, address, phone, email). There are **no income, expense, or
   asset overlay positions**, so every `$ ____` field on the 6-page form ships blank —
   "My total monthly income is $ ___", the expenses table, and the assets table are all
   empty.
2. **False "public assistance" declaration.** `fee_waiver_checkbox_overrides` hardcodes
   `cb_1_1: True` and `cb_1_2: True` ("I receive public assistance" = Yes), while the
   specific program boxes (`cb_1_6` SNAP, `cb_1_8` Medicaid) correctly stay Off. A tenant
   with **no benefits** therefore files a form that both says "I receive public
   assistance" and leaves it blank.

Root cause: MN's fee waiver is a scanned form whose financial fields were never wired into
the overlay. It needs income/expense/asset overlay positions (like the answer form's
explanation lines) and the `cb_1_1`/`cb_1_2` override made conditional on
`receives_public_benefits`.

## 🟡 Minor

1. **LA fee waiver — SNAP checkbox not marked.** Jerome has `receives_snap=True`, and the
   financial table is filled correctly, but the SNAP benefit checkbox on the LA fee waiver
   isn't checked (text not found). Verify the benefit mapping.

## 🟡 Chat UX issues (cross-cutting — still present across all states)

1. **`{"phase_completed": N}` markers leak into user-visible text** (observed in LA, KY,
   and earlier in IL/Denver). The regex strips only one marker; when the agent emits
   several at once they surface to the customer.
2. **Internal defense keys shown to the user** ("def_repairs — …", "def_continuance — …")
   in KY/LA/MI lists, despite the system prompt saying to read only the wording.
3. **Stray artifacts after dollar-amount confirmations** — a bare "json" (KY) and "00."
   (CO/CT) appear in otherwise clean messages.
4. **Dollar-amount re-confirmation is frequent** — the agent often asks "is that $X?" for
   rent/amount figures (adds friction; consider stricter amount extraction).

## Still open (from prior passes)

- **IL fee waiver** — Medicaid/LIHEAP-only tenant still gets a false "public benefit"
  declaration + no financial data (see `docs/state-qa-findings.md`). Not addressed yet.
- **GA "reduced rent"** — auto-fills `$775 × 2` for a `$1,550`/month tenant; verify mapping.
- **DOB** — now supported in schema/prompt (commit `ebf2e7b`); needs an end-to-end re-run
  to confirm it reaches the forms.
