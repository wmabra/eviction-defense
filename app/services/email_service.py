"""Simple email sending for support notifications.

Uses SendGrid when configured, falls back to logging only.
"""
import logging
from app.config import settings

logger = logging.getLogger(__name__)


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email. Returns True if sent, False if logged only."""
    if not settings.sendgrid_api_key:
        logger.info(f"EMAIL (no SendGrid configured) — To: {to} — Subject: {subject}")
        logger.info(f"Body: {body}")
        return False

    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail

        message = Mail(
            from_email="support@evictions.help",
            to_emails=to,
            subject=subject,
            plain_text_content=body,
        )
        sg = SendGridAPIClient(settings.sendgrid_api_key)
        response = sg.send(message)
        logger.info(f"Email sent to {to}: {response.status_code}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {e}")
        return False


def send_callback_email(
    callback_id: str,
    first_name: str,
    last_name: str,
    phone: str,
    best_time: str,
    case_id: str,
    issue: str,
    caller_email: str = "",
) -> bool:
    """Send same-day callback notification to support@evictions.help."""
    subject = f"Callback Request: {first_name} {last_name} — {issue[:60]}"

    body = f"""CALLBACK REQUEST — {callback_id}

Name: {first_name} {last_name}
Phone: {phone}
Best time to call: {best_time} Eastern

Case ID: {case_id or 'No case — pre-sale or not identified'}
Caller Email: {caller_email or 'Not provided'}

Issue:
{issue}

---
This is an automated notification from the evictions.help voice agent.
Callback was requested on {callback_id[:8]}.
Please call back TODAY.
"""

    return send_email(
        to="support@evictions.help",
        subject=subject,
        body=body,
    )
