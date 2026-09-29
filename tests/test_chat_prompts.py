"""Unit tests for chat prompt generation and state separation."""
import pytest
from app.services.chat import (
    build_system_prompt,
    SERVED_STATES,
    STATE_NAMES,
    STATE_NAME_TO_CODE,
)


def test_connecticut_prompt_cleanliness():
    """Verify Connecticut prompt contains only CT-specific questions and zero CO leakage."""
    prompt = build_system_prompt("CT", "Hartford")

    # Positive assertions
    assert "Connecticut (CT)" in prompt
    assert "Housing Court / Superior Court" in prompt
    assert "Form JD-HM-5" in prompt
    assert "def_paid" in prompt
    assert "TFA" in prompt
    assert "total number of dependents" in prompt.lower()

    # Negative assertions (no Colorado or other state leaks)
    assert "Colorado Courts E-Filing" not in prompt
    assert "Denver" not in prompt
    assert "Aid to the Blind" not in prompt
    assert "Old Age Pension" not in prompt
    assert "judge trial or a jury trial" not in prompt
    assert "what is the name of your bank" not in prompt.lower()
    assert "names, ages, and relationships to you" not in prompt


def test_colorado_statewide_prompt():
    """Verify Colorado statewide prompt includes JDF 103, Section 7e, CoS, and JDF 205 items."""
    prompt = build_system_prompt("CO", "Arapahoe")

    assert "Colorado (CO)" in prompt
    assert "JDF 103" in prompt
    assert "Section 7e" in prompt
    assert "Colorado Courts E-Filing" in prompt
    assert "judge trial or a jury trial" in prompt
    assert "Aid to the Blind" in prompt
    assert "Old Age Pension" in prompt
    assert "what is the name of your bank" in prompt.lower()
    assert "household members schedule" in prompt


def test_colorado_denver_prompt():
    """Verify Denver County Court uses narrative answer form instruction."""
    prompt = build_system_prompt("CO", "Denver")

    assert "Denver County Court" in prompt
    assert "DCC CP No. 3" in prompt
    assert "NARRATIVE ANSWER FORM" in prompt


def test_all_20_states_no_leakage():
    """Verify all 20 states generate valid prompts without cross-state pollution."""
    assert len(SERVED_STATES) == 20

    for st in SERVED_STATES:
        prompt = build_system_prompt(st, "TestCounty")
        assert len(prompt) > 1000, f"Prompt too short for {st}"
        assert STATE_NAMES[st] in prompt, f"State name missing in {st} prompt"

        if st != "CO":
            assert "Colorado Courts E-Filing" not in prompt, f"Colorado E-Filing leaked into {st}"
            assert "Denver" not in prompt, f"Denver leaked into {st}"
            assert "Aid to the Blind" not in prompt, f"CO Aid to the Blind leaked into {st}"


def test_state_normalization():
    """Verify full state names and case variations normalize properly."""
    assert STATE_NAME_TO_CODE.get("CONNECTICUT") == "CT"
    assert STATE_NAME_TO_CODE.get("COLORADO") == "CO"
    assert STATE_NAME_TO_CODE.get("TEXAS") == "TX"

    p1 = build_system_prompt("connecticut", "Hartford")
    p2 = build_system_prompt("CT", "Hartford")
    assert p1 == p2
