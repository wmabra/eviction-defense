# Tenant Eviction Defense — Intake Questionnaire Design

## Overview

The intake form is the foundation of the entire system. Every downstream piece (OCR extraction, confirmation screen, document generation, SMS reminders) depends on the data collected here.

**Flow:** Pre-Screen (before payment) → Payment → Full Questionnaire → Document Upload → AI Extraction → Confirmation → Packet Generation

---

## Section 1: Pre-Screen (Before Payment)

These questions determine eligibility. If the case can't be handled, auto-decline before they pay.

| # | Question | Type | Options / Validation | Route if Blocking |
|---|---|---|---|---|
| 1.1 | What state is your eviction in? | Dropdown | All 50 states | If not FL → "Coming soon" |
| 1.2 | What county is your case in? | Dropdown | FL counties list | Validates against covered counties |
| 1.3 | Are you the tenant named in the eviction? | Yes/No | | If No → redirect |
| 1.4 | Is this a residential rental property? | Yes/No | | If No → auto-decline (commercial) |
| 1.5 | Have you received court papers (summons + complaint)? | Yes/No | | If No → redirect to "wait until you're served" |
| 1.6 | Has a sheriff's eviction notice been posted or have you received a writ of possession? | Yes/No | | If Yes → auto-decline (past the point of help) |
| 1.7 | Do you receive Section 8 / housing vouchers / live in public housing? | Yes/No | | If Yes → auto-decline (special rules, attorney referral) |
| 1.8 | Are you on active military duty? | Yes/No | | If Yes → auto-decline (SCRA protections, attorney referral) |
| 1.9 | Have you filed for bankruptcy? | Yes/No | | If Yes → auto-decline |
| 1.10 | Do you have your eviction papers ready to upload? | Yes/No | | If No → "You'll need them to proceed" |

**Eligibility rules:**

- Florida + residential + tenant + served with papers + no sheriff/writ + no Section 8 + no military + no bankruptcy = eligible
- Everything else = auto-decline with referral message

---

## Section 2: Personal & Property Info (Post-Payment)

| # | Field | Type | Validation | Notes |
|---|---|---|---|---|
| 2.1 | full_name | Text | Required | As it appears on lease/court papers |
| 2.2 | also_known_as | Text | Optional | Any aliases or nicknames used |
| 2.3 | co_tenants | Text[] | Optional | Names of other tenants on the lease |
| 2.4 | property_address | Text (multi-line) | Required | Full street address, unit # |
| 2.5 | property_city | Text | Required | |
| 2.6 | property_zip | Text | 5-digit | |
| 2.7 | county | Text | From pre-screen, editable | Pre-filled from Section 1 |
| 2.8 | phone | Phone | Required | For SMS reminders |
| 2.9 | email | Email | Required | For packet delivery |
| 2.10 | mailing_address | Text | Same as property or different | Some tenants don't want paper at the property |

---

## Section 3: Landlord / Plaintiff Info

| # | Field | Type | Validation | Notes |
|---|---|---|---|---|
| 3.1 | landlord_name | Text | Required | Full legal name or LLC name |
| 3.2 | landlord_address | Text | Required | For service of documents |
| 3.3 | landlord_phone | Phone | Optional | |
| 3.4 | landlord_email | Email | Optional | |
| 3.5 | landlord_attorney_name | Text | Conditional | If landlord has a lawyer |
| 3.6 | landlord_attorney_email | Email | Conditional | For e-service |
| 3.7 | property_manager | Text | Optional | |
| 3.8 | management_company | Text | Optional | |

---

## Section 4: Eviction Case Details

| # | Field | Type | Validation | Notes |
|---|---|---|---|---|
| 4.1 | case_number | Text | Required | Format: CACE-YYYY-XXXXX |
| 4.2 | court_name | Text | Required | e.g. "County Court in and for Miami-Dade County" |
| 4.3 | court_location | Text | Required | Specific courthouse address |
| 4.4 | judge_assigned | Text | Optional | If known |
| 4.5 | received_3day_notice | Yes/No | Required | |
| 4.6 | notice_date | Date | Conditional | Only if 4.5 = Yes |
| 4.7 | notice_received_date | Date | Conditional | When they actually got the notice |
| 4.8 | notice_amount_demanded | Currency | Conditional | Amount landlord claimed in notice |
| 4.9 | received_summons | Yes/No | Required | |
| 4.10 | summons_service_date | Date | Conditional | The date they were served |
| 4.11 | summons_service_method | Dropdown | Conditional | In person / Posted on door / Mail / Other |
| 4.12 | complaint_amount_claimed | Currency | Conditional | Amount from the complaint |
| 4.13 | court_date | Date | Optional | If a hearing is already scheduled |
| 4.14 | response_deadline | Date | Calculated | 5 business days from service — THE critical date |
| 4.15 | has_attorney | Yes/No | Required | Does tenant have a lawyer? |

---

## Section 5: Rent & Payment History

| # | Field | Type | Validation | Notes |
|---|---|---|---|---|
| 5.1 | monthly_rent | Currency | Required | Per lease |
| 5.2 | rent_due_day | Number | 1-31 | Day of month rent is due |
| 5.3 | agree_with_amount | Yes/No | Required | Does tenant agree with what landlord claims? |
| 5.4 | amount_tenant_believes_owed | Currency | If 5.3 = No | What tenant thinks is actually owed |
| 5.5 | why_disagree | Text (multi-line) | If 5.3 = No | Explanation |
| 5.6 | paid_after_notice | Yes/No | Required | |
| 5.7 | amount_paid_after_notice | Currency | Conditional | |
| 5.8 | date_paid | Date | Conditional | |
| 5.9 | has_proof_of_payment | Yes/No | Conditional | |
| 5.10 | sent_7day_repair_notice | Yes/No | Required | Key defense: tenant must have SENT written notice |
| 5.11 | repair_notice_date | Date | Conditional | |
| 5.12 | repair_notice_details | Text | Conditional | What was wrong |
| 5.13 | landlord_response_to_repair | Text | Conditional | Did landlord fix it? |
| 5.14 | applied_for_rental_assistance | Yes/No | Required | |
| 5.15 | rental_assistance_status | Dropdown | Conditional | Pending / Approved / Denied |
| 5.16 | rental_assistance_amount | Currency | Conditional | |

---

## Section 6: Defenses (from Form 1.947(b))

Check all that apply. Each maps to a numbered defense on the official form.

| # | Defense | Code | Conditional Explanation |
|---|---|---|---|
| 6a | Landlord did not make repairs, I withheld rent after written notice | DEF_REPAIRS | Requires 7-day notice sent |
| 6b | I don't owe the amount claimed / Motion to Determine Rent | DEF_AMOUNT | Requires explaining why |
| 6c | I tried to pay but landlord wouldn't accept | DEF_ATTEMPTED_PAY | |
| 6d | I already paid the rent demanded | DEF_PAID | Requires proof |
| 6e | Landlord waived/canceled the notice | DEF_WAIVED | |
| 6f | Retaliatory eviction | DEF_RETALIATION | Tenant complained to authorities |
| 6g | Fair Housing Act violation | DEF_FAIR_HOUSING | Discrimination |
| 6h | Landlord accepted rent after the notice | DEF_ACCEPTED_RENT | |
| 6i | I already corrected the lease violation | DEF_CORRECTED | |
| 6j | Landlord is not the owner | DEF_NOT_OWNER | |
| 6k | I didn't receive the notice or it was legally incorrect | DEF_BAD_NOTICE | |
| 6l | Other defenses | DEF_OTHER | Free text |

For each checked defense, the system prompts:
> "Please briefly explain the facts supporting this defense:"
> (multi-line text, required)

---

## Section 7: Additional Requests & Preferences

| # | Field | Type | Options | Notes |
|---|---|---|---|---|
| 7.1 | needs_more_time | Yes/No | | Hardship letter trigger |
| 7.2 | hardship_reason | Text | Conditional | Job loss, medical, death in family, etc. |
| 7.3 | wants_payment_plan | Yes/No | | Landlord letter trigger |
| 7.4 | payment_plan_amount | Currency | Conditional | How much they can pay per month |
| 7.5 | trial_by | Radio | Judge / Jury | From Form 1.947(b) section 5 |
| 7.6 | needs_filing_fee_waiver | Yes/No | | Indigency info trigger |
| 7.7 | has_eviction_defense_attorney | Yes/No | | Route to attorney if yes |
| 7.8 | additional_notes | Text (multi-line) | Optional | Anything else |

---

## Section 8: Document Upload

| # | Field | Format | Required? | Notes |
|---|---|---|---|---|
| 8.1 | notice_3day | PDF/IMG | Conditional | Required if received notice |
| 8.2 | summons | PDF/IMG | Strongly recommended | Critical for case number + deadline |
| 8.3 | complaint | PDF/IMG | Strongly recommended | Critical for amount claimed |
| 8.4 | lease | PDF/IMG | Recommended | Defines "rent", supports defenses |
| 8.5 | payment_proof | PDF/IMG | If paid | Receipts, bank statements, check copies |
| 8.6 | rent_ledger | PDF/IMG | Optional | |
| 8.7 | repair_notice | PDF/IMG | If sent 7-day notice | Written notice to landlord |
| 8.8 | landlord_communications | PDF/IMG | Optional | Emails, texts, letters |
| 8.9 | rental_assistance_proof | PDF/IMG | Conditional | |
| 8.10 | other_documents | PDF/IMG | Optional | |

**Upload rules:**

- Max 20MB per file
- Accepts: PDF, JPG, PNG
- Each upload tagged with what type of document it is
- System runs OCR + AI extraction on each

---

## Data Schema (JSON)

```json
{
  "case_metadata": {
    "id": "uuid",
    "created_at": "ISO datetime",
    "status": "pre_screen | payment_pending | intake_in_progress | intake_complete | extraction_pending | confirmation_pending | packet_ready | delivered | declined | refunded"
  },
  "pre_screen": {
    "state": "FL",
    "county": "string",
    "is_tenant": true,
    "is_residential": true,
    "received_court_papers": true,
    "has_writ_or_sheriff": false,
    "is_section_8": false,
    "is_active_military": false,
    "has_bankruptcy": false,
    "has_documents": true,
    "eligible": true
  },
  "personal_info": {
    "full_name": "string",
    "also_known_as": "string",
    "co_tenants": ["string"],
    "property_address": "string",
    "property_city": "string",
    "property_zip": "string",
    "county": "string",
    "phone": "string",
    "email": "string",
    "mailing_address": "string"
  },
  "landlord_info": {
    "landlord_name": "string",
    "landlord_address": "string",
    "landlord_phone": "string",
    "landlord_email": "string",
    "landlord_attorney_name": "string",
    "landlord_attorney_email": "string",
    "property_manager": "string",
    "management_company": "string"
  },
  "case_details": {
    "case_number": "string",
    "court_name": "string",
    "court_location": "string",
    "judge_assigned": "string",
    "received_3day_notice": true,
    "notice_date": "date",
    "notice_received_date": "date",
    "notice_amount_demanded": 0.00,
    "received_summons": true,
    "summons_service_date": "date",
    "summons_service_method": "in_person | posted | mail | other",
    "complaint_amount_claimed": 0.00,
    "court_date": "date",
    "response_deadline": "date",
    "has_attorney": false
  },
  "rent_payment": {
    "monthly_rent": 0.00,
    "rent_due_day": 1,
    "agree_with_amount": true,
    "amount_tenant_believes_owed": 0.00,
    "why_disagree": "string",
    "paid_after_notice": false,
    "amount_paid_after_notice": 0.00,
    "date_paid": "date",
    "has_proof_of_payment": false,
    "sent_7day_repair_notice": false,
    "repair_notice_date": "date",
    "repair_notice_details": "string",
    "landlord_response_to_repair": "string",
    "applied_for_rental_assistance": false,
    "rental_assistance_status": "pending | approved | denied",
    "rental_assistance_amount": 0.00
  },
  "defenses": {
    "def_repairs": {"checked": false, "explanation": ""},
    "def_amount": {"checked": false, "explanation": ""},
    "def_attempted_pay": {"checked": false, "explanation": ""},
    "def_paid": {"checked": false, "explanation": ""},
    "def_waived": {"checked": false, "explanation": ""},
    "def_retaliation": {"checked": false, "explanation": ""},
    "def_fair_housing": {"checked": false, "explanation": ""},
    "def_accepted_rent": {"checked": false, "explanation": ""},
    "def_corrected": {"checked": false, "explanation": ""},
    "def_not_owner": {"checked": false, "explanation": ""},
    "def_bad_notice": {"checked": false, "explanation": ""},
    "def_other": {"checked": false, "explanation": ""}
  },
  "preferences": {
    "needs_more_time": false,
    "hardship_reason": "string",
    "wants_payment_plan": false,
    "payment_plan_amount": 0.00,
    "trial_by": "judge | jury",
    "needs_filing_fee_waiver": false,
    "has_eviction_defense_attorney": false,
    "additional_notes": "string"
  },
  "documents": [
    {
      "type": "notice_3day | summons | complaint | lease | payment_proof | rent_ledger | repair_notice | landlord_communications | rental_assistance_proof | other",
      "filename": "string",
      "filepath": "string",
      "uploaded_at": "ISO datetime",
      "ocr_text": "string (populated after processing)",
      "extracted_fields": {}
    }
  ],
  "extracted_data": {
    "status": "pending | processing | ready | conflict",
    "fields": {
      "customer_name": {"value": "", "source": "intake | document", "confirmed": false},
      "tenant_names": {"value": [], "source": "", "confirmed": false},
      "property_address": {"value": "", "source": "", "confirmed": false},
      "county": {"value": "", "source": "", "confirmed": false},
      "court_name": {"value": "", "source": "", "confirmed": false},
      "case_number": {"value": "", "source": "", "confirmed": false},
      "landlord_name": {"value": "", "source": "", "confirmed": false},
      "amount_claimed": {"value": 0, "source": "", "confirmed": false},
      "notice_date": {"value": null, "source": "", "confirmed": false},
      "service_date": {"value": null, "source": "", "confirmed": false},
      "court_date": {"value": null, "source": "", "confirmed": false},
      "response_deadline": {"value": null, "source": "", "confirmed": false}
    },
    "conflicts": []
  },
  "packet": {
    "status": "not_generated | generated | downloaded",
    "documents_generated": [],
    "generated_at": null,
    "delivery_email_sent": false,
    "delivery_sms_sent": false
  }
}
```
