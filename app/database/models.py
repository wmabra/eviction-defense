"""Case profile database models."""
import uuid
from datetime import datetime, date
from sqlalchemy import (
    Column, String, Float, Boolean, Date, DateTime, JSON, Text, Integer
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.dialects.sqlite import TEXT as SQLITE_TEXT


class Base(DeclarativeBase):
    pass


def generate_uuid():
    return str(uuid.uuid4())


class Case(Base):
    __tablename__ = "cases"

    id = Column(String, primary_key=True, default=generate_uuid)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = Column(String, default="pre_screen", index=True)

    # Pre-screen
    county = Column(String, nullable=False)
    eligible = Column(Boolean, default=False)
    ineligibility_reason = Column(Text, nullable=True)

    # Stripe
    stripe_payment_intent_id = Column(String, nullable=True)
    payment_status = Column(String, default="unpaid")

    # Personal info (intake)
    full_name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    property_address = Column(Text, nullable=True)
    property_city = Column(String, nullable=True)
    property_zip = Column(String, nullable=True)
    mailing_address = Column(Text, nullable=True)
    co_tenants = Column(JSON, nullable=True)

    # Landlord info
    landlord_name = Column(String, nullable=True)
    landlord_address = Column(Text, nullable=True)
    landlord_phone = Column(String, nullable=True)
    landlord_email = Column(String, nullable=True)
    landlord_attorney_name = Column(String, nullable=True)
    landlord_attorney_email = Column(String, nullable=True)

    # Case details
    case_number = Column(String, nullable=True)
    court_name = Column(String, nullable=True)
    received_3day_notice = Column(Boolean, nullable=True)
    notice_received_date = Column(Date, nullable=True)
    notice_amount_demanded = Column(Float, nullable=True)
    received_summons = Column(Boolean, nullable=True)
    summons_service_date = Column(Date, nullable=True)
    summons_service_method = Column(String, nullable=True)
    complaint_amount_claimed = Column(Float, nullable=True)
    court_date = Column(Date, nullable=True)
    response_deadline = Column(Date, nullable=True)
    monthly_rent = Column(Float, nullable=True)
    agree_with_amount = Column(Boolean, nullable=True)
    amount_tenant_believes_owed = Column(Float, nullable=True)

    # Defenses (JSON blob of checked defenses + explanations)
    defenses = Column(JSON, nullable=True)

    # Preferences
    trial_by = Column(String, default="judge")
    needs_more_time = Column(Boolean, default=False)
    wants_payment_plan = Column(Boolean, default=False)
    needs_filing_fee_waiver = Column(Boolean, default=False)

    # AI extraction
    extraction_status = Column(String, default="pending")
    extracted_data = Column(JSON, nullable=True)
    extraction_confirmed = Column(Boolean, default=False)
    confirmation_token = Column(String, nullable=True)

    # Packet
    packet_status = Column(String, default="not_generated")
    packet_paths = Column(JSON, nullable=True)
    packet_generated_at = Column(DateTime, nullable=True)

    # Delivery
    delivery_email_sent = Column(Boolean, default=False)
    delivery_sms_sent = Column(Boolean, default=False)


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    case_id = Column(String, index=True, nullable=False)
    doc_type = Column(String, nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    ocr_text = Column(SQLITE_TEXT, nullable=True)
    ocr_processed = Column(Boolean, default=False)
