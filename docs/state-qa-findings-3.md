# State-by-State Packet QA — NM, OH, OK, OR, RI (John Doe)

**Date:** 2026-09-28
**Tester:** QA (John Doe test-packet generator + programmatic field inspection)
**Code under test:** `main` @ `3068b8b`
**Method:** Fresh packets generated via `scripts/generate_test_packet.py` (which mirrors
`POST /api/v1/admin/generate-test-packet`), using the built-in John Doe persona for each
state. Note: this is the **test-packet path**, not the live chat-intake flow — intake
coverage is out of scope for this pass.

| State | County | Persona | Docs | Automated audit | Verdict |
|-------|--------|---------|------|-----------------|---------|
| NM | Bernalillo | John Doe (Albuquerque) | 21 | 0 errors / 0 warnings | ✅ works — ⚠️ fee waiver minimal |
| OH | Franklin | John Doe (Columbus) | 21 | 0 errors / 0 warnings | ✅ works |
| OK | Oklahoma | John Doe (Oklahoma City) | 21 | 0 errors / 0 warnings | ✅ works — note asset fields |
| OR | Multnomah | John Doe (Portland) | 21 | 0 errors / 0 warnings | ⚠️ defenses not auto-filled |
| RI | Providence | John Doe (Providence) | 21 | 0 errors / 0 warnings | ✅ works |

## Artifacts

Per-state unpacked packet + individual zip in `test_packages/`:

```
test_packages/<STATE>_John_Doe/          # 21 PDFs (00 cover → 20 bankruptcy notice)
test_packages/<STATE>_John_Doe_packet.zip
```

All five are bundled for the developer in:
`~/Downloads/eviction-defense-qa_NM-OH-OK-OR-RI.zip` (one folder per state + these notes).

## Automated checks

`tests/audit_packet.py` run against each of the 5 packets:

- **Signature auto-fill:** 0 (no `/s/` leaks; signature lines stay blank for ink)
- **Widget collisions/overlaps:** 0
- **Orphan pages:** 0
- **Checkbox exclusivity (Yes/No + pay-frequency):** 0 contradictions
- **Result: 0 errors, 0 warnings across all 5 states.**

## Per-state findings

### ✅ NM — Bernalillo (works; fee waiver is caption-only)

- **Answer form (`nm_form_4-907.pdf`)** — narrative defenses filled correctly:
  `defense_narrative_1` ("Conditions: …heat and hot water…"), `_2` ("Amount disputed…"),
  `_3` ("Defective notice…"). Caption (court type, county, case #, plaintiff, defendant,
  property address, city/state/zip, phone) all present.
- **⚠️ Fee waiver (`nm_fee_waiver.pdf`)** — only caption fields are populated: `county`,
  `case_number`, `full_name`, and the page-5 `date`. **No financial data and no
  public-benefit checkbox are filled.** The config's `fee_waiver_overlay` maps exactly
  these 4 fields and nothing else. John Doe has `receives_snap=True` +
  `receives_medicaid=True` and full income/expense data, none of which reaches the form.
  **Please confirm the NM fee waiver is complete as-is** — if the form has an "I receive
  public assistance" box or income/expense blanks, they ship empty.

### ✅ OH — Franklin (works)

- **Answer form** — narrative defense paragraph + caption (county, case #, plaintiff,
  defendant, address, phone) filled. Date/printed-name present.
- **Fee waiver (`oh_fee_waiver.pdf`)** — financial path filled: employment income,
  monthly gross, rent, utilities, food, transportation, medical. Cash/checking/child-care/
  debt fields are blank only because the John Doe test data has no asset/child-care/debt
  values (not a code issue).

### ✅ OK — Oklahoma (works; asset fields blank by test data)

- **Answer form** — narrative defense + caption (county, case #, plaintiff, defendant,
  address, phone) filled. Date/printed-name present.
- **Fee waiver (`ok_fee_waiver_fillable.pdf` — Pauper's Affidavit)** — employment income,
  rent, and utilities filled. `cash_on_hand`, `checking_balance`, and `vehicle_value` are
  mapped in config but ship blank because the John Doe test data provides no assets.
  Confirm the chat intake actually collects these (else real customers get the same
  blanks).

### ⚠️ OR — Multnomah (defenses not auto-filled — highest priority)

- **Answer form (`or_eviction_answer.pdf`)** — caption + signature block fill correctly
  (county, case #, landlord, tenant name, address, city/state/zip, phone, email, date,
  printed name). **But none of the tenant's defenses are applied:** the form is a scanned
  PDF whose 10 defense checkboxes are auto-detected as editable fields, yet the OR config
  has **no `defense_options` mapping** — only caption overlay positions. John Doe selects
  `def_repairs` / `def_amount` / `def_bad_notice`, and none of those checkboxes get
  checked (0 defense checkboxes, no defense narrative).
  - **Recommendation:** wire OR's 10 defense checkboxes to `defense_options` (like MN
    HOU202 / RI / MO do) so the selected defenses are pre-checked, or confirm that leaving
    them for manual user selection is intended.
- **Fee waiver (`or_fee_waiver.pdf` — OJD Fee Deferral/Waiver)** — caption fills on pages
  1 and 4, plus one benefit checkbox (`vcb_1_11 = Yes`). No financial fields (categorical
  form). Confirm the checked benefit box is the correct one for SNAP/Medicaid.

### ✅ RI — Providence (works)

- **Answer form (`ri_eviction_answer.pdf`)** — caption + certificate of service filled;
  two defense checkboxes auto-checked: `def_failed_maintain` ("…failed to maintain…")
  and `def_no_notice` ("…have not received the required notice…"). Note: RI's answer form
  has **no "dispute amount" defense option**, so John Doe's `def_amount` is (correctly)
  not reflected — confirm that's intended for RI.
- **Fee waiver** — caption (petitioner/respondent, file #, date, phone, county) plus
  household-size (`= 1`) and monthly-gross (`= 2,200.00`) filled.

## Cross-cutting notes

1. All five packets fill the signature `date` with the generation date (`09/28/2026`).
2. John Doe financial data omits assets (cash/checking/vehicle) and child-care/debt
   figures, so any fee-waiver field for those categories ships blank across OH/OK — a
   test-data gap, not a filler bug. Worth keeping in mind when reviewing the fee waivers.
3. OR is the only one of the five with a genuine defense-mapping gap; NM's sparse fee
   waiver is the second item to verify.
