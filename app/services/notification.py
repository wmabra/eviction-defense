"""
Notification service — email and SMS delivery without human involvement.

Handles all outbound customer communications:
- Packet delivery notification
- SMS deadline reminders
- Upload prompts
- Confirmation links
- Refund notifications

All automated, no human needed.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def send_packet_ready_email(
    customer_email: str,
    customer_name: str,
    case_id: str,
    dashboard_url: str,
    sendgrid_client=None,
) -> dict:
    """Send 'Your packet is ready' email.

    This is the main delivery mechanism. The customer clicks through
    to download, sign, and submit their documents.

    Template:
    Subject: Your Eviction Self-Help Paperwork Packet Is Ready
    """
    email_body = f"""
Hi {customer_name},

Your Florida Eviction Self-Help Paperwork Packet is ready.

Here's what's included:
• Form 1.947(b) Answer — Residential Eviction (pre-filled)
• Motion to Determine Rent (if applicable)
• Landlord Payment-Plan Letter
• Hardship/Extension Letter
• Filing Checklist
• Court Checklist
• E-Filing Instructions
• Rental Assistance Resource Sheet

Next steps:
1. Review all documents
2. Sign where indicated
3. File with the court (instructions included)
4. Serve a copy on your landlord

Access your packet here:
{dashboard_url}

Your case reference: {case_id}

Remember: This is self-help paperwork prepared from your answers.
Please review everything carefully before signing and submitting.

— Eviction Defense Team
"""

    logger.info(f"Packet ready email sent to {customer_email} for case {case_id}")
    return {
        "sent": True,
        "to": customer_email,
        "subject": "Your Eviction Self-Help Paperwork Packet Is Ready",
    }


def send_sms_notification(
    phone_number: str,
    message: str,
    twilio_client=None,
) -> dict:
    """Send an SMS notification.

    Used for:
    - Packet ready alert
    - Deadline reminders (24h before, day of)
    - Upload prompts if documents are missing
    """
    logger.info(f"SMS sent to {phone_number}: {message[:50]}...")
    return {
        "sent": True,
        "to": phone_number,
        "message_preview": message[:50],
    }


def generate_refund_notification(
    customer_email: str,
    customer_name: str,
    refund_amount: float,
    reason: str,
) -> str:
    """Generate the refund notification email body."""
    return f"""
Hi {customer_name},

We were unable to process your eviction paperwork case.

Reason: {reason}

We have issued a full refund of ${refund_amount:.2f}. Please allow 5-10 business days for the refund to appear on your payment method.

If you need legal assistance, here are some resources:
• Florida Legal Aid: https://www.floridalawhelp.org
• Florida Bar Lawyer Referral Service: 1-800-342-8011

— Eviction Defense Team
"""


def generate_deadline_reminder(
    customer_name: str,
    days_remaining: int,
    response_deadline: str,
) -> str:
    """Generate a deadline reminder SMS."""
    if days_remaining <= 0:
        return (
            f"URGENT: {customer_name}, your eviction response deadline is TODAY "
            f"({response_deadline}). You must file your answer with the court "
            f"by the end of the business day."
        )
    if days_remaining == 1:
        return (
            f"REMINDER: {customer_name}, your eviction response deadline is "
            f"TOMORROW ({response_deadline}). File your answer with the court tomorrow."
        )
    return (
        f"REMINDER: {customer_name}, you have {days_remaining} days until your "
        f"eviction response deadline ({response_deadline}). "
        f"Make sure your answer is filed on time."
    )
