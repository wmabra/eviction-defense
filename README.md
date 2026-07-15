# Eviction Defense — Automated Self-Help Paperwork

AI-powered document preparation for tenants facing eviction in 20 states.

**Price:** $395 flat fee  
**Domain:** evictions.help  
**Model:** No-touch software workflow — customer answers, uploads, confirms, and receives a ready-to-file paperwork packet.

## What's Included ($395 Packet)

1. Form 1.947(b) Answer — Residential Eviction (pre-filled)
2. Motion to Determine Rent (when applicable)
3. Landlord Payment-Plan Letter
4. Hardship/Extension Letter
5. Filing Checklist (step-by-step)
6. Court Checklist (what to bring to hearing)
7. E-Filing Instructions (myflcourtaccess.com)
8. Rental Assistance Resource Sheet (county-specific)
9. SMS Deadline Reminders

## Customer Workflow

```
Landing Page → Pre-Screen → Payment → Questionnaire → Upload Docs 
→ AI Extraction → Customer Confirmation → Packet Generation → Delivery
```

## Tech Stack

- **Backend:** Python 3.11+, FastAPI
- **PDF Generation:** python-docx + ReportLab
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **OCR:** Google Document AI
- **AI Extraction:** OpenAI API (structured outputs)
- **Payments:** Stripe
- **Automation:** n8n or custom
- **SMS:** Twilio
- **Email:** SendGrid / Postmark
- **Frontend:** Simple HTML/JS or React (TBD)

## Project Structure

```
eviction-defense/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings & env vars
│   ├── database/models.py   # SQLAlchemy models
│   ├── schema/              # Pydantic models (intake, case, extraction)
│   ├── routers/             # API endpoints
│   ├── services/            # Business logic
│   └── templates/counties/  # County-specific data
├── schema/                  # Design docs
└── tests/
```

## Development Setup

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your keys
uvicorn app.main:app --reload
```

## Legal Notice

This service prepares self-help legal paperwork based on your answers. It does not provide legal advice or representation. You are responsible for reviewing, signing, and submitting all documents. If you need legal advice, consult a licensed Florida attorney.
