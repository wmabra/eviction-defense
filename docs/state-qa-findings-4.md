# State-by-State Packet QA — SC, TN, TX, VA (John Doe)

**Date:** 2026-09-28
**Tester:** QA (John Doe test-packet generator + programmatic field inspection)
**Code under test:** `main` @ `f3fac3c`
**Method:** Fresh packets via `scripts/generate_test_packet.py` (mirrors
`POST /api/v1/admin/generate-test-packet`), built-in John Doe persona per state.
Test-packet path, not the live chat-intake flow.

| State | County | Persona | Docs | Automated audit | Verdict |
|-------|--------|---------|------|-----------------|---------|
| SC | Richland | John Doe (Columbia) | 21 | 0 errors / 0 warnings | ⚠️ fee-waiver field leak |
| TN | Davidson | John Doe (Nashville) | 21 | 0 errors / 0 warnings | ⚠️ fee waiver caption-only |
| TX | Harris | John Doe (Houston) | 21 | 0 errors / 0 warnings | 🔴 amount defense dropped + FW over-check |
| VA | Fairfax | John Doe (Fairfax) | 21 | 0 errors / 0 warnings | ✅ works (single grounds box) |

## Artifacts

```
test_packages/<STATE>_John_Doe/          # 21 PDFs
test_packages/<STATE>_John_Doe_packet.zip
```

All four bundled for the developer in:
`~/Downloads/eviction-defense-qa_SC-TN-TX-VA.zip` (one folder per state + these notes).

## Automated checks

`tests/audit_packet.py` on each of the 4 packets: **0 errors, 0 warnings**
(signature auto-fill, widget collisions, orphan pages, checkbox exclusivity all clean).

## 🔴 Critical findings

### 1. TX — amount-dispute defense is never checked (field-name mismatch)

The TX answer config maps `def_amount → "Check Box54"` (no space), but the actual
widget on `tx_eviction_answer.pdf` is named **`"Check Box 54"`** (with a space).
John Doe has `def_amount=True`, yet the box stays `Off` — only `Check Box7` (repairs)
and `Check Box10` (notice) get checked.

```python
# app/services/state_configs.py, TX defense_options
{"key": "def_amount", "label": "Amount claimed is incorrect", "field": "Check Box54"},  # ← wrong
```

**Fix:** change to `"Check Box 54"`.

### 2. TX — fee waiver benefit checkboxes over-checked (7 boxes, false declaration)

The TX fee waiver (`tx_fee_waiver.pdf`) ships with **7 benefit boxes auto-checked**
(`vcb_0_30` … `vcb_0_36`: SNAP, TANF, Medicaid, CHIP, SSI, WIC, AABD) even though
John Doe only has `receives_snap=True` + `receives_medicaid=True`. The benefit
instruction line ("…Food stamps/SNAP TANF Medicaid CHIP SSI WIC AABD…") is a single
horizontal run of text, so the label-proximity auto-detection in
`_map_fee_waiver_checkboxes` can't isolate individual boxes and over-checks. This
files a **false public-benefit declaration** (perjury risk).

**Fix:** give TX an explicit `fee_waiver_checkbox_map` (or `fee_waiver_checkbox_overrides`)
mapping only the specific SNAP/Medicaid boxes, instead of relying on label auto-detection.

### 3. SC — landlord name leaks into "Plaintiff's Address / Age / Occupation"

On the SC fee waiver, three fields are filled with the landlord's *name*
("Palmetto Property Group, LLC") instead of their intended value:

```
Plaintiff's Address    = "Palmetto Property Group, LLC"   (should be landlord address)
Plaintiff's Age        = "Palmetto Property Group, LLC"   (wrong — an LLC has no age)
Plaintiff's Occupation = "Palmetto Property Group, LLC"   (wrong)
```

This is a substring false-match ("Plaintiff" → `landlord_name`) in the generic
field matcher. `Plaintiff's Employer` correctly stays blank.

**Fix:** scope the SC fee-waiver matching so `landlord_name` fills only
`Plaintiff Name`, and `landlord_address` fills `Plaintiff's Address`; leave
`Age`/`Occupation` blank (we don't collect them for the landlord).

## 🟡 Verify items

### 4. SC — "deny all" checked, but the reason text is blank

The SC answer checks `I deny that I am responsible at all` (driven by `def_repairs` +
`def_bad_notice`), but the paired explanation field
`"Reason Not Responsible at All For Amount Claimed…"` ships **empty** — the tenant's
specific reasons ("heat and hot water intermittent…", "did not receive notice…") are
not written in. Confirm the defense explanations are meant to populate these reason
fields (`field_mapping_defense_explanation`).

### 5. TN — fee waiver is caption-only

`tn_fee_waiver.pdf` overlay maps only `case_number`, `county`, `full_name`,
`full_address`, `phone`. **No financial or public-benefit fields** are filled (same
pattern as NM). Confirm the TN fee waiver is complete as-is, or wire in the
income/expense/benefit data.

### 6. VA — single grounds checkbox for all defenses

All six VA `defense_options` map to the same field `User.CB1`. So John Doe's three
defenses collapse to one checked box (`User.CB1 = 1`) with no differentiation on the
form. Confirm the specific grounds are captured elsewhere (or are intentionally left
for the user to write). (VA fee waiver is otherwise solid — SNAP box + income +
household + medical filled correctly.)

### 7. TN — year field uses 2 digits

The TN answer date is split across `day_2=28`, `mm_1=9`, `year_2=26` (2-digit).
Likely correct for the form, but flagging in case it should be `2026`.

## Cross-cutting

- All four packets fill the signature `date` with the generation date (`09/28/2026`).
- The John Doe data omits assets (cash/checking/vehicle) and child-care/debt figures,
  so fee-waiver fields for those categories ship blank where the config maps them
  (SC/VA) — a test-data gap, not a filler bug.
