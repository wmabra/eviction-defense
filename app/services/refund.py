"""
Auto-refund service — handles automated refunds for declined cases.

If the system cannot process a case safely (risk flags, wrong state, etc.),
it should auto-refund without human intervention.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def process_auto_refund(
    case_id: str,
    payment_intent_id: str,
    reason: str,
    stripe_client,
) -> dict:
    """Process a full refund for a declined case.

    This is called automatically when the legal risk gate or eligibility
    check determines the case cannot be handled.

    Args:
        case_id: Our internal case ID
        payment_intent_id: Stripe PaymentIntent ID to refund
        reason: Why the refund is being processed
        stripe_client: Stripe API client

    Returns:
        dict with refund status
    """
    try:
        refund = stripe_client.Refund.create(
            payment_intent=payment_intent_id,
            reason="requested_by_customer",
            metadata={
                "case_id": case_id,
                "refund_reason": reason,
                "auto_refund": "true",
            },
        )

        logger.info(
            f"Auto-refund processed for case {case_id}: "
            f"PaymentIntent {payment_intent_id}, reason: {reason}"
        )

        return {
            "success": True,
            "refund_id": refund.id,
            "amount": refund.amount,
            "status": refund.status,
            "message": f"Your payment of ${refund.amount / 100:.2f} has been refunded. "
                       f"Please allow 5-10 business days for the refund to appear.",
        }

    except Exception as e:
        logger.error(f"Auto-refund failed for case {case_id}: {e}")
        return {
            "success": False,
            "error": str(e),
            "message": "We encountered an issue processing your refund. "
                       "Please contact support for assistance.",
        }


def generate_refund_deadline_message(case_id: str) -> str:
    """Generate a message about refund timing.

    Our policy: full refund within 24 hours of purchase if packet not yet generated.
    No refunds after packet is delivered (customer can choose not to use it).
    """
    return (
        "Since we were unable to process your case, we have issued a full refund. "
        "You should see the funds returned to your payment method within 5-10 business days."
    )


CHECK_ELIGIBILITY_ROUTE_REFUND_MAP = {
    "state_not_supported": "We only support Florida at this time.",
    "county_not_supported": "Your county is not yet supported.",
    "writ_sheriff_involved": "Writ of possession or sheriff involvement requires legal representation.",
    "section_8": "Section 8/public housing cases require an attorney.",
    "active_military": "Active military SCRA cases require legal assistance.",
    "bankruptcy": "Bankruptcy cases require coordination with your bankruptcy attorney.",
}

# 24-hour money-back guarantee auto message
REFUND_POLICY_MESSAGE = (
    "We offer a full refund if we cannot prepare your packet, "
    "or if you cancel within 24 hours of purchase before the packet is generated."
)
