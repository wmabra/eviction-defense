"""
Three automation gates that eliminate the need for human QA.

Gate 1 - Document Quality Gate: If uploaded docs are blurry, missing pages, or unreadable,
the system auto-responds asking for better uploads. No human needed.

Gate 2 - Data Mismatch Gate: If the customer's questionnaire answers conflict with what's
extracted from their documents, the system flags the discrepancy and asks the customer
to resolve it. No human needed.

Gate 3 - Legal Risk Gate: If the case hits a risk flag (court tomorrow, sheriff involved,
Section 8, active military, etc.), the system auto-declines and offers a refund.
No human needed.
"""

from typing import Any


class GateResult:
    """Result from an automation gate check."""
    def __init__(self, passed: bool, message: str = "", requires_action: bool = False):
        self.passed = passed
        self.message = message
        self.requires_action = requires_action

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "message": self.message,
            "requires_action": self.requires_action,
        }


# ---- Gate 1: Document Quality Gate ----

def check_document_quality(ocr_text: str | None, filename: str = "") -> GateResult:
    """Check if an uploaded document is readable and has content.

    This runs after OCR. If OCR returns empty or garbage, we ask for a re-upload.
    """
    if not ocr_text or len(ocr_text.strip()) < 10:
        return GateResult(
            passed=False,
            message=(
                f"We could not clearly read your file '{filename or 'uploaded document'}'. "
                "Please upload a clearer photo or PDF. Make sure the text is well-lit, "
                "in focus, and not blurry."
            ),
            requires_action=True,
        )

    # Check for gibberish (very low ratio of alphanumeric to total chars)
    alpha_chars = sum(c.isalnum() for c in ocr_text)
    if len(ocr_text) > 0 and (alpha_chars / len(ocr_text)) < 0.3:
        return GateResult(
            passed=False,
            message=(
                f"The file '{filename}' doesn't appear to contain readable text. "
                "Please upload a clear scan or photo of your document."
            ),
            requires_action=True,
        )

    return GateResult(passed=True)


def check_all_document_quality(documents: list[dict]) -> list[GateResult]:
    """Run quality check on all uploaded documents."""
    results = []
    for doc in documents:
        result = check_document_quality(
            ocr_text=doc.get("ocr_text"),
            filename=doc.get("filename", ""),
        )
        results.append(result)
    return results


# ---- Gate 2: Data Mismatch Gate ----

def check_for_data_mismatches(
    intake_data: dict[str, Any],
    extracted_data: dict[str, Any],
) -> list[GateResult]:
    """Compare customer's intake answers with AI-extracted document data.

    If they conflict on critical fields (county, case number, dates), flag it
    for the customer to resolve before generation.
    """
    mismatches = []
    critical_fields = [
        ("county", "the county where your case is filed"),
        ("case_number", "your case number"),
        ("court_name", "the court name"),
    ]

    for field_key, field_label in critical_fields:
        intake_val = intake_data.get(field_key)
        extracted_val = extracted_data.get(field_key)

        if intake_val and extracted_val and str(intake_val).lower() != str(extracted_val).lower():
            mismatches.append(GateResult(
                passed=False,
                message=(
                    f"We found conflicting information about **{field_label}**. "
                    f"You told us: **{intake_val}**. "
                    f"Your document says: **{extracted_val}**. "
                    "Please confirm which is correct before we prepare your packet."
                ),
                requires_action=True,
            ))

    return mismatches


# ---- Gate 3: Legal Risk Gate ----

def check_legal_risk_flags(case_data: dict) -> list[GateResult]:
    """Check for high-risk situations that should auto-decline.

    This runs after the full intake + extraction, as a final safety check
    before document generation.
    """
    flags = []

    # Court date too soon (less than 24 hours)
    court_date = case_data.get("court_date")
    if court_date:
        from datetime import datetime, timedelta
        court_dt = datetime.strptime(str(court_date), "%Y-%m-%d") if isinstance(court_date, str) else court_date
        if court_dt and court_dt < datetime.now() + timedelta(hours=24):
            flags.append(GateResult(
                passed=False,
                message=(
                    "Your court date is less than 24 hours away. "
                    "Our system needs time to prepare your packet. "
                    "Please contact the court clerk immediately to ask about your options, "
                    "or visit the courthouse self-help center in person."
                ),
                requires_action=False,  # Not resolvable - must decline
            ))

    # Sheriff/writ already involved
    if case_data.get("has_writ_or_sheriff"):
        flags.append(GateResult(
            passed=False,
            message=(
                "A writ of possession has been issued or the sheriff is involved. "
                "This is past the point where our self-help packet can help. "
                "Please contact a licensed Florida attorney or your local legal aid organization immediately."
            ),
            requires_action=False,
        ))

    # Section 8 / public housing
    if case_data.get("is_section_8"):
        flags.append(GateResult(
            passed=False,
            message=(
                "Section 8/public housing evictions have special federal rules. "
                "This case requires an attorney or legal aid. "
                "We can offer a full refund."
            ),
            requires_action=False,
        ))

    # Active military
    if case_data.get("is_active_military"):
        flags.append(GateResult(
            passed=False,
            message=(
                "Active military personnel have special protections under the Servicemembers "
                "Civil Relief Act (SCRA). Please contact your base legal assistance office."
            ),
            requires_action=False,
        ))

    # Bankruptcy
    if case_data.get("has_bankruptcy"):
        flags.append(GateResult(
            passed=False,
            message=(
                "Bankruptcy triggers an automatic stay that affects eviction proceedings. "
                "Please consult with your bankruptcy attorney before proceeding."
            ),
            requires_action=False,
        ))

    return flags


def get_actionable_issues(
    quality_results: list[GateResult],
    mismatch_results: list[GateResult],
    risk_results: list[GateResult],
) -> list[dict]:
    """Aggregate all gate results into a customer-facing list of issues to resolve."""
    issues = []

    for result in quality_results + mismatch_results:
        if not result.passed and result.requires_action:
            issues.append(result.to_dict())

    # If any risk flags exist, the case is auto-declined
    risk_failures = [r for r in risk_results if not r.passed]
    if risk_failures:
        issues.append({
            "passed": False,
            "message": "Your case has been flagged for the following reason(s):",
            "requires_action": False,
        })
        for r in risk_failures:
            issues.append(r.to_dict())
        issues.append({
            "passed": False,
            "message": (
                "We can process a full refund. Please check your email for refund instructions, "
                "or contact us if you believe this is an error."
            ),
            "requires_action": False,
        })

    return issues
