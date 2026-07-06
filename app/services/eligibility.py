"""Eligibility rules engine for pre-screening."""
from app.schema.intake import PreScreen


# Florida counties we currently support
SUPPORTED_COUNTIES = {
    "Miami-Dade", "Broward", "Duval", "Hillsborough", "Orange",
    "Palm Beach", "Polk", "Pinellas", "Volusia", "Lee",
    "Leon", "Seminole", "Osceola", "Pasco", "Brevard",
}

# Eviction stages we can handle (in order)
HANDLED_STAGES = {
    "notice_received": "You have received a 3-day notice but not yet been served with a lawsuit.",
    "served": "You have been served with an eviction summons and complaint.",
}


def check_eligibility(pre_screen: PreScreen) -> dict:
    """Run pre-screen checks and return eligibility result.

    Returns:
        dict with keys: eligible (bool), reason (str or None), message (str)
    """
    reasons = []

    # State check
    if pre_screen.state.upper() != "FL":
        return {
            "eligible": False,
            "reason": "state_not_supported",
            "message": "We currently only support Florida eviction cases. Other states coming soon."
        }

    # County check
    if pre_screen.county not in SUPPORTED_COUNTIES:
        return {
            "eligible": False,
            "reason": "county_not_supported",
            "message": (
                f"We're building county-by-county. {pre_screen.county} isn't live yet. "
                f"Supported: {', '.join(sorted(SUPPORTED_COUNTIES))}."
            )
        }

    # Must be the tenant
    if not pre_screen.is_tenant:
        reasons.append("This service is for tenants named in the eviction.")

    # Must be residential
    if not pre_screen.is_residential:
        reasons.append("We can only handle residential evictions, not commercial.")

    # Must have court papers (served with summons)
    if not pre_screen.received_court_papers:
        reasons.append(
            "You need to have been served with court papers (summons and complaint) "
            "before we can prepare your answer packet."
        )

    # Too late - writ/sheriff stage
    if pre_screen.has_writ_or_sheriff:
        reasons.append(
            "A writ of possession has been issued or the sheriff is involved. "
            "This is past the point where our self-help packet can help. "
            "Please contact a lawyer or legal aid immediately."
        )

    # Section 8 / Public housing
    if pre_screen.is_section_8:
        reasons.append(
            "Section 8/public housing evictions have special federal rules. "
            "This case requires an attorney or legal aid. Our self-help packet is not appropriate."
        )

    # Active military
    if pre_screen.is_active_military:
        reasons.append(
            "Active military personnel have special protections under the SCRA. "
            "This requires legal advice. Please contact a military legal assistance office."
        )

    # Bankruptcy
    if pre_screen.has_bankruptcy:
        reasons.append(
            "Bankruptcy triggers an automatic stay that affects eviction proceedings. "
            "Please consult with your bankruptcy attorney."
        )

    if reasons:
        return {
            "eligible": False,
            "reason": "; ".join(reasons),
            "message": (
                "Based on your answers, your situation may require legal advice or direct representation. "
                "Our self-help paperwork software is not the right fit for this case. "
                "We recommend contacting a Florida licensed attorney or your local legal aid organization."
            )
        }

    return {
        "eligible": True,
        "reason": None,
        "message": "You're eligible! Proceed to purchase your self-help packet."
    }


def get_stage_label(has_notice: bool, has_summons: bool, has_writ: bool) -> str:
    """Determine what stage the eviction is in."""
    if has_writ:
        return "writ_issued"
    if has_summons:
        return "served"
    if has_notice:
        return "notice_received"
    return "unknown"
