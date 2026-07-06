"""Tests for the eligibility rules engine."""
import pytest
from app.schema.intake import PreScreen
from app.services.eligibility import check_eligibility


def test_eligible_standard_case():
    """A standard Florida tenant should be eligible."""
    screen = PreScreen(
        state="FL",
        county="Miami-Dade",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == True
    assert result["reason"] is None


def test_declined_wrong_state():
    """Non-Florida cases should be declined."""
    screen = PreScreen(
        state="TX",
        county="Miami-Dade",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False
    assert result["reason"] == "state_not_supported"


def test_declined_writ_sheriff():
    """Writ of possession should decline."""
    screen = PreScreen(
        state="FL",
        county="Broward",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=True,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False


def test_declined_section_8():
    """Section 8 cases should decline."""
    screen = PreScreen(
        state="FL",
        county="Duval",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=True,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False


def test_declined_military():
    """Active military should decline."""
    screen = PreScreen(
        state="FL",
        county="Orange",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=True,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False


def test_declined_bankruptcy():
    """Bankruptcy should decline."""
    screen = PreScreen(
        state="FL",
        county="Palm Beach",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=True,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False


def test_unsupported_county():
    """An unsupported county should decline."""
    screen = PreScreen(
        state="FL",
        county="Glades",
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False
    assert result["reason"] == "county_not_supported"


def test_declined_no_court_papers():
    """Cannot help if tenant hasn't been served yet."""
    screen = PreScreen(
        state="FL",
        county="Miami-Dade",
        is_tenant=True,
        is_residential=True,
        received_court_papers=False,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    result = check_eligibility(screen)
    assert result["eligible"] == False


def test_all_supported_counties():
    """All 15 supported counties should work."""
    counties = [
        "Miami-Dade", "Broward", "Duval", "Hillsborough", "Orange",
        "Palm Beach", "Polk", "Pinellas", "Volusia", "Lee",
        "Leon", "Seminole", "Osceola", "Pasco", "Brevard",
    ]
    for county in counties:
        screen = PreScreen(
            state="FL",
            county=county,
            is_tenant=True,
            is_residential=True,
            received_court_papers=True,
            has_writ_or_sheriff=False,
            is_section_8=False,
            is_active_military=False,
            has_bankruptcy=False,
            has_documents_to_upload=True,
        )
        result = check_eligibility(screen)
        assert result["eligible"] == True
