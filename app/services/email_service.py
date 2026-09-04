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


def send_welcome_email(to: str, temp_password: str) -> bool:
    """Send the post-payment account-creation email with login credentials."""
    subject = "Your evictions.help account is ready"
    base = settings.app_url.rstrip("/")

    body = f"""Welcome to evictions.help — your payment is confirmed and your account is ready.

Your account details:
  Username: {to}
  Password: {temp_password}

To get started:
1. Go to {base}/account
2. Log in with the username and password above
3. Click "Start" to begin your intake with our AI assistant

For your security, please change your password after logging in (Settings → Change Password).

You can log back in anytime to pick up right where you left off — your progress is saved automatically.

Need help? Reply to this email or contact support@evictions.help.

— The evictions.help team
"""

    return send_email(to=to, subject=subject, body=body)


def send_password_reset_email(to: str, temp_password: str) -> bool:
    """Send a password-reset email with a new temporary password."""
    subject = "Your evictions.help password has been reset"
    base = settings.app_url.rstrip("/")

    body = f"""A password reset was requested for your evictions.help account.

Your new temporary password:
  Username: {to}
  Password: {temp_password}

To log in:
1. Go to {base}/account
2. Enter the username and password above

For your security, please change this password after logging in (Settings → Change Password).

If you did not request this reset, you can ignore this email — but your previous password is no longer active.

— The evictions.help team
"""

    return send_email(to=to, subject=subject, body=body)


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
