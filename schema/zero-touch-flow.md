# Zero-Touch Automation Flow

This document traces a customer's journey through the system end-to-end,
showing exactly where automation replaces human work.

---

## The Complete Flow

```
                     ╔═══════════════════════╗
                     ║    CUSTOMER LANDS     ║
                     ╚═══════════════════════╝
                               │
                     ┌─────────▼─────────┐
                     │  1. PRE-SCREEN    │ ← Automated eligibility engine
                     │   (9 questions)   │    (app/services/eligibility.py)
                     └─────────┬─────────┘
                               │
                    ┌──────────▼──────────┐
                    │     Eligible?       │
                    └────┬──────────┬─────┘
                    YES  │          │  NO
                         │          │
              ┌──────────▼──┐  ┌───▼──────────┐
              │  2. PAYMENT │  │ Auto-decline │ ← NO human involved
              │   ($395)    │  │ + auto-refund │    (app/services/refund.py)
              └──────┬──────┘  └──────────────┘
                     │
              ┌──────▼─────────────────────────┐
              │  3. FULL INTAKE QUESTIONNAIRE   │ ← Branching logic based on
              │     (~40 questions, 8 sections) │    answers. No human reads these.
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼──────────────────┐
              │  4. DOCUMENT UPLOAD              │
              │     (notice, summons, lease...)  │
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼──────────────────┐
              │  5. AI EXTRACTION PIPELINE       │ ← GATE 1: Document Quality
              │     OCR → AI → structured fields │    (app/services/gates.py)
              └──────────────┬──────────────────┘    (app/services/extraction.py)
                             │
                    ┌────────▼────────┐
                    │  GATE 2: DATA  │ ← Flags conflicts between intake
                    │  MISMATCH CHECK│    answers and document extraction.
                    └────────┬────────┘    Customer resolves it, not a human.
                             │
                    ┌────────▼────────┐
                    │  GATE 3: LEGAL │ ← Auto-declines high-risk cases.
                    │  RISK CHECK    │    (court in <24h, sheriff, SCRA, etc.)
                    └────────┬────────┘
                             │
              ┌──────────────▼──────────────────┐
              │  6. CUSTOMER CONFIRMATION        │ ← ★ REPLACES THE QA PERSON ★
              │     Review & approve every field  │    (app/services/confirmation.py)
              │     Sign confirmation statement   │
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼──────────────────┐
              │  7. PACKET GENERATION            │
              │     PDF documents from templates  │
              │     • Form 1.947(b) Answer       │
              │     • Motion to Determine Rent   │
              │     • Hardship letter            │
              │     • Payment-plan letter        │
              │     • Filing checklist           │
              │     • Court checklist            │
              │     • E-filing instructions      │
              │     • Rental assistance sheet    │
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼──────────────────┐
              │  8. DELIVERY + REMINDERS         │ ← SMS + email, all automated
              │     • "Packet ready" email       │    (app/services/notification.py)
              │     • SMS alert                  │
              │     • Deadline reminders (D-2,   │
              │       D-1, D-Day) via Twilio     │
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼──────────────────┐
              │  9. AI SUPPORT BOT               │ ← Only answers process questions
              │     • "Where is my packet?"      │    Never gives legal advice.
              │     • "How do I upload?"         │
              │     • "What does case number     │
              │        mean?"                   │
              └──────────────┬──────────────────┘
                             │
              ┌──────────────▼────┐
              │  CUSTOMER REVIEWS │
              │  SIGNS, & SUBMITS │ ← Final step, done by customer
              └───────────────────┘
```

## Where Humans Are NOT Needed

| Task | Automated By | File |
|---|---|---|
| Eligibility screening | Rules engine | `eligibility.py` |
| Payment processing | Stripe | (webhook) |
| Document reading | Google Doc AI + OpenAI | `extraction.py` |
| Data validation | Gate 1 (quality) | `gates.py` |
| Conflict resolution | Gate 2 (mismatch) → customer resolves | `gates.py` |
| Risk assessment | Gate 3 (legal risk) → auto-decline | `gates.py` |
| Fact confirmation | Customer confirmation screen | `confirmation.py` |
| Document generation | Python PDF engine | (next build step) |
| Packet delivery | Email + SMS | `notification.py` |
| Deadline reminders | Twilio + cron | `notification.py` |
| Support (process Qs) | AI chatbot (trained on FAQ only) | (next build step) |
| Refunds | Auto-triggered on decline | `refund.py` |

## The One Thing The Customer Does That Replaced An Employee

**The confirmation screen.** Instead of paying a QA person $15-20/hr to verify
names, dates, case numbers, and counties, the system:

1. Extracts the data with AI
2. Shows it to the customer
3. Forces them to confirm or correct each field
4. Requires a signed statement: *"I confirm this information is accurate..."*

The customer is the expert on their own case. They will catch errors faster
than any QA person would, and they bear responsibility for accuracy.

## Automation Boundaries (What The System Won't Touch)

The AI support bot will answer:
✓ Process questions (how to upload, download, sign, file)
✓ Definition questions (what is a case number, what is a summons)
✓ Status questions (where is my packet, when will it be ready)

The AI support bot will NOT answer:
✗ "Should I pay my rent?"
✗ "Will I win my case?"
✗ "What defense should I use?"
✗ "Is my landlord breaking the law?"

For legal questions, the bot responds:
> "That is a legal-advice question. Our service prepares self-help paperwork
> based on your answers, but we do not provide legal advice or representation.
> You may want to speak with a licensed attorney or local legal aid organization."
