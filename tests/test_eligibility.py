"""Tests for the eligibility rules engine (20-state product).

Data-driven off app.services.eligibility's own SUPPORTED_STATES /
SUPPORTED_COUNTIES, so these tests cannot silently rot when states are added
or removed again — which is exactly what happened to the previous version of
this file: every case was hardcoded to a since-removed state, so all nine
cases were exercising "state is unsupported" rather than the rule they
claimed to test.

Each declining test asserts the SPECIFIC reason, never just
`eligible == False`. Asserting the boolean alone previously produced five
false passes — the cases declined because that state was gone, not because of
the rule under test, so the decline rules had no real coverage at all.
"""
import pytest

from app.schema.intake import PreScreen
from app.services.eligibility import (
    SUPPORTED_COUNTIES,
    SUPPORTED_STATES,
    check_eligibility,
)

# A state deliberately not in the product (removed with FL / AZ / NV / MA).
UNSUPPORTED_STATE = "CA"

# Reference supported state + one real county in it, taken from the engine.
SUPPORTED_STATE = "VA"
SUPPORTED_COUNTY = "Norfolk"


def screen(**overrides) -> PreScreen:
    """A fully eligible pre-screen with individual answers overridden.

    Built as a real PreScreen and overridden with ``model_copy`` rather than a
    mixed ``str | bool`` dict spread into ``PreScreen(**base)``, which erased
    every field's declared type and let a mistaken ``screen(state=True)`` pass
    unreviewed.
    """
    base = PreScreen(
        state=SUPPORTED_STATE,
        county=SUPPORTED_COUNTY,
        is_tenant=True,
        is_residential=True,
        received_court_papers=True,
        has_writ_or_sheriff=False,
        is_section_8=False,
        is_active_military=False,
        has_bankruptcy=False,
        has_documents_to_upload=True,
    )
    return base.model_copy(update=overrides) if overrides else base


def test_reference_fixtures_are_self_consistent():
    """Guard the guards: the reference state/county must actually be supported."""
    assert SUPPORTED_STATE in SUPPORTED_STATES
    assert SUPPORTED_COUNTY in SUPPORTED_COUNTIES[SUPPORTED_STATE]
    assert UNSUPPORTED_STATE not in SUPPORTED_STATES


# ── the happy path ──

def test_eligible_standard_case():
    """A standard tenant in a supported state/county is eligible."""
    result = check_eligibility(screen())
    assert result["eligible"] is True
    assert result["reason"] is None


@pytest.mark.parametrize("state", sorted(SUPPORTED_STATES))
def test_every_supported_state_is_accepted(state):
    """No published state may be rejected."""
    counties = SUPPORTED_COUNTIES.get(state) or {""}
    county = sorted(counties)[0]
    result = check_eligibility(screen(state=state, county=county))
    assert result["eligible"] is True, f"{state}/{county}: {result['reason']}"


def test_all_supported_counties_are_accepted():
    """Every county the engine publishes must actually pass pre-screen."""
    failures = []
    for state, counties in sorted(SUPPORTED_COUNTIES.items()):
        for county in sorted(counties):
            result = check_eligibility(screen(state=state, county=county))
            if result["eligible"] is not True:
                failures.append(f"{state}/{county}: {result['reason']}")
    assert not failures, (
        f"{len(failures)} published counties are rejected, e.g. {failures[:10]}"
    )


# ── coverage-area declines (state / county) ──

def test_declined_unsupported_state():
    """A state outside the 20 is declined for the STATE, not the county."""
    result = check_eligibility(screen(state=UNSUPPORTED_STATE, county="Bogus County"))
    assert result["eligible"] is False
    assert result["reason"] == "state_not_supported"


def test_declined_unsupported_county():
    """A county outside the state's live list is declined for the COUNTY."""
    result = check_eligibility(screen(county="Definitely Not A County"))
    assert result["eligible"] is False
    assert result["reason"] == "county_not_supported"


# ── rule declines: each asserts its OWN reason ──

def test_declined_no_court_papers():
    result = check_eligibility(screen(received_court_papers=False))
    assert result["eligible"] is False
    assert "served with court papers" in result["reason"].lower()


def test_declined_writ_sheriff():
    result = check_eligibility(screen(has_writ_or_sheriff=True))
    assert result["eligible"] is False
    assert "writ of possession" in result["reason"].lower()


def test_declined_section_8():
    result = check_eligibility(screen(is_section_8=True))
    assert result["eligible"] is False
    assert "section 8" in result["reason"].lower()


def test_declined_military():
    result = check_eligibility(screen(is_active_military=True))
    assert result["eligible"] is False
    assert "scra" in result["reason"].lower() or "military" in result["reason"].lower()


def test_declined_bankruptcy():
    result = check_eligibility(screen(has_bankruptcy=True))
    assert result["eligible"] is False
    assert "bankruptcy" in result["reason"].lower()


def test_declined_not_tenant():
    result = check_eligibility(screen(is_tenant=False))
    assert result["eligible"] is False
    assert "tenants" in result["reason"].lower()


def test_declined_commercial_unit():
    result = check_eligibility(screen(is_residential=False))
    assert result["eligible"] is False
    assert "residential" in result["reason"].lower()


def test_multiple_decline_reasons_are_combined():
    """Several disqualifiers at once should all be reported, not just the first."""
    result = check_eligibility(screen(is_tenant=False, has_bankruptcy=True))
    assert result["eligible"] is False
    assert "tenants" in result["reason"].lower()
    assert "bankruptcy" in result["reason"].lower()
