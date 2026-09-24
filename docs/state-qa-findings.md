# State-by-State End-to-End User QA — CO, CT, GA, IL, IN

**Date:** 2026-09-24
**Tester:** QA (simulated end-users, full website flow: eligibility → chat intake → packet generation)
**Code under test:** `main` @ `ebf2e7b` (includes the developer's Denver-narrative/DOB fix
`ebf2e7b`, landed mid-QA and re-verified).

Five states were driven through the **real chat intake** (live DeepSeek agent, ~45 turns
each), exactly as a website user would — not via the admin test-packet shortcut.

| State | County | Persona | Docs | Verdict |
|-------|--------|---------|------|---------|
| CO | Jefferson | Elena Marie Vasquez (Lakewood) | 17 | ✅ works |
| CT | Hartford | Darnell Brooks | 17 | ✅ works |
| GA | Fulton | Aisha Johnson (Atlanta) | 17 | ⚠️ 1 suspect field |
| IL | Cook | Robert Kowalski (Chicago) | 17 | 🔴 fee waiver broken |
| IN | Marion | Tanya Patel (Indianapolis) | 18 | ✅ works |

## Artifacts

Each state's packet + chat transcript + extracted data:

```
~/Downloads/eviction-defense-qa/<STATE>/
├── packet.zip          # the generated ZIP
├── unzipped/           # all PDFs
├── chat_extracted.json # structured data the agent produced
└── (chat history in /tmp/chat_cases/<STATE>/history.json)
```

## ✅ Confirmed working (all 5 states)

- **Full flow** — eligibility pre-screen passed, 6-phase chat completed, packet generated
  with no server errors.
- **Answer forms** — tenant name, case number, landlord name, property address, phone,
  email, and certificate of service all filled correctly on every state's form.
- **Defenses** — the tenant's selected defenses map to the correct form checkboxes in all
  5 states (CO JDF 103 `7A/7E` boxes, CT `RENTACCEPTED/NORENTDUE/CODEVIOLA`, GA
  `Reason.*`/`FailedToRepair`, IL numbered checkboxes, IN narrative).
- **Narrative states** — IN and GA correctly build a multi-defense narrative paragraph
  from the `def_*` checkboxes (unlike Denver's free-form narrative bug).
- **Fee waiver** — correct in CO (SNAP auto-qualify), CT (full financial), GA (SNAP+Medicaid
  + full financial), IN (full financial: income, expenses, totals).

## 🔴 Critical — Illinois fee waiver is broken (IL/Cook)

Robert (Medicaid + energy assistance, **no** SSI/SNAP/TANF) gets a fee waiver that is
**filed with a false benefit declaration and no financial data**:

- `15 - Checkboxes` = *"I checked one of the public benefit boxes in section 3."* — but
  **none** of the section-3 boxes (SSI `10`, AABD `11`, GA `12`, SNAP `13`, TANF `14`) are
  checked.
- `18 - My Employment` = **"No"** (Robert is employed — should be "Yes").
- All income / expense / asset fields are **blank**.

**Root cause:** the fee-waiver filler treats *any* `receives_public_benefits` (here Medicaid
or energy assistance) as IL auto-qualification. IL's form only auto-qualifies on
SSI/AABD/GA/SNAP/TANF. Medicaid/energy assistance are **not** on that list, so the form
must go through the full financial path instead of skipping it. This needs a fix — a
tenant who only has Medicaid/LIHEAP would file an inaccurate fee waiver.

## ⚠️ Verify — Georgia "reduced rent" fields (GA/Fulton)

Aisha's answer form auto-populates:

- `Property.ReducedRentAmt` = `775.00`
- `Property.ReducedRentNumberMonths` = `2`

Her monthly rent is **$1,550** and she believes she owes **$1,550 (one month)**. `$775 × 2`
looks like the code halved the amount across two months. The GA "reduced rent" box is
about the property's *value being reduced by defects*, so this auto-fill may be
semantically wrong. Worth confirming the intended mapping.

## 🟡 DOB drop — addressed in code, needs end-to-end re-verification

This QA pass observed the chat agent asking for date of birth in **every** intake while
`PersonalInfo` had no `date_of_birth` field, so it never reached `extracted_data` or the
forms. The developer's follow-up commit `ebf2e7b` **adds** `date_of_birth` to
`PersonalInfo` (`app/schema/intake.py`), to the system prompt's extraction list, and to the
fee-waiver field mappings — so it is fixed at the code level. This pass's chat transcripts
predate that commit, so a fresh intake re-run is still needed to confirm end-to-end.

## 🟡 Chat UX issues (cross-cutting, seen across multiple states)

1. **`{"phase_completed": N}` markers leak into user-visible text** (seen in IL and Denver).
   The regex in `get_chat_response` strips only one marker; when the agent emits several at
   once (or the progress marker at an unexpected point) they surface to the customer.
2. **Stray `00.` appears after some dollar-amount confirmations** (e.g. "Thank you — $2,600.
   00. Do you have a court date scheduled?"). Cosmetic but unprofessional.
3. **CT defense list shows internal keys** to the user ("def_paid — I paid the rent") instead
   of only the wording, despite the system prompt saying to read only the wording.
4. **Dollar-amount re-confirmation is frequent** — the agent often asks "is that $X?" for
   rent/amount figures. Not a bug, but adds friction; consider stricter amount extraction.

## Prior finding — now fixed ✅

The **Denver narrative-answer bug** (see `docs/denver-qa-findings.md`) was fixed in
developer commit `ebf2e7b`. Re-verified: the Denver `defense_narrative` field now contains
the tenant's actual story ("…broken furnace…", "…rental assistance…", "$1,925, not
$3,850") instead of the generic boilerplate. The five states in this doc use `def_*`
checkboxes and were never affected.
