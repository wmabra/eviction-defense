"""
Tests for Colorado Denver (DCC CP No. 3) and Statewide (JDF 103 / JDF 205) packet generation,
verifying answer forms, fee waivers, certificate of service, and defense checklists.
"""
import os
import sys
import copy
import tempfile
import pymupdf
from pathlib import Path

# Ensure app is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_test_packet import CO, CO_DENVER
from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver
from app.services.chat import build_system_prompt


def test_colorado_prompts():
    """Verify chat system prompts for Denver vs Statewide Colorado."""
    prompt_denver = build_system_prompt("CO", "Denver")
    prompt_jefferson = build_system_prompt("CO", "Jefferson")

    # Denver uses narrative answer form (DCC CP No. 3)
    assert "DCC CP No. 3" in prompt_denver
    assert "NARRATIVE ANSWER FORM" in prompt_denver
    assert "Section 7a" not in prompt_denver
    assert "Colorado Courts E-Filing" in prompt_denver

    # Statewide (Jefferson) uses JDF 103 with Sections 7a through 7e
    assert "Section 7a" in prompt_jefferson
    assert "Section 7e" in prompt_jefferson
    assert "judge trial or a jury trial" in prompt_jefferson
    assert "Colorado Courts E-Filing" in prompt_jefferson
    assert "household members schedule" in prompt_jefferson
    assert "name of your bank" in prompt_jefferson


def test_denver_answer_form_and_cos():
    """Verify Denver County Court DCC CP No. 3 form overlay, alignment, and e-filing."""
    data = copy.deepcopy(CO_DENVER["data"])
    data["preferences"]["certificate_of_service_method"] = "efile"
    data["preferences"]["trial_by"] = "jury"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "denver_answer.pdf")
        ok = fill_answer_form(data, "CO", out_pdf)
        assert ok is True
        assert os.path.exists(out_pdf)

        doc = pymupdf.open(out_pdf)
        assert len(doc) == 2

        # Page 1 checks
        p1_widgets = {w.field_name: w.field_value for w in doc[0].widgets()}
        assert p1_widgets.get("plaintiff_name") == "Mile High Property Group, LLC"
        assert p1_widgets.get("defendant_name") == "John Doe"
        assert "John Doe" in p1_widgets.get("party_info", "")
        assert "1450 S Pearl Street, Denver, CO 80210" in p1_widgets.get("party_info", "")
        assert p1_widgets.get("case_number") == "2024CV12345"
        assert "heating system has been broken" in p1_widgets.get("defense_narrative", "")
        assert p1_widgets.get("checkbox_hearing_in_person") == "Yes"

        # Page 2 checks
        p2_widgets = {w.field_name: w.field_value for w in doc[1].widgets()}
        assert p2_widgets.get("full_address") == "1450 S Pearl Street, Denver, CO 80210"
        assert p2_widgets.get("checkbox_trial_jury") == "Yes"
        assert p2_widgets.get("checkbox_cos_efile") == "Yes"
        assert p2_widgets.get("checkbox_cos_mail") in ("", "Off", None)
        assert "Susan Advocate" in p2_widgets.get("cos_recipient", "")


def _get_page_widgets(page) -> dict[str, str]:
    """Extract widgets, preserving selected value for radio groups."""
    res = {}
    for w in page.widgets():
        val = w.field_value
        if val not in ("", "Off", None, False) or w.field_name not in res:
            res[w.field_name] = str(val)
    return res


def test_colorado_statewide_jdf103():
    """Verify Colorado statewide JDF 103 form with Section 7e defenses and jury demand."""
    data = copy.deepcopy(CO["data"])
    data["preferences"]["trial_by"] = "jury"
    data["preferences"]["certificate_of_service_method"] = "regular_mail"

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "co_answer.pdf")
        ok = fill_answer_form(data, "CO", out_pdf)
        assert ok is True
        assert os.path.exists(out_pdf)

        doc = pymupdf.open(out_pdf)
        assert len(doc) == 6

        # Page 1: Jury trial demand
        p1_widgets = _get_page_widgets(doc[0])
        assert p1_widgets.get("√  Jury Trial") == "Yes"
        assert p1_widgets.get("Court County") == "Jefferson"
        assert p1_widgets.get("Case Number") == "2024C030123"

        # Page 2: Section 7A
        p2_widgets = _get_page_widgets(doc[1])
        assert p2_widgets.get("7A.4") == "Yes"

        # Page 3: Section 7D & 7E
        p3_widgets = _get_page_widgets(doc[2])
        assert p3_widgets.get("7D.1") == "Yes"
        assert p3_widgets.get("7E.1") == "Yes"
        assert p3_widgets.get("7E.2") == "Yes"
        assert p3_widgets.get("7E.3") == "Yes"

        # Page 5: Certificate of service by mail
        p5_widgets = _get_page_widgets(doc[4])
        assert "regular mail" in str(p5_widgets.get("Group_CoS"))
        assert "Summit Ridge" in str(p5_widgets.get("CoS_Mail"))


def test_colorado_fee_waiver_household_and_bank():
    """Verify JDF 205 fee waiver Section 8 household parsing and Section 10 bank name."""
    data = copy.deepcopy(CO["data"])
    data["financial_info"]["household_members"] = "Jane Doe (34, Spouse), Tommy Doe (8, Child)"
    data["financial_info"]["bank_name"] = "FirstBank"
    data["financial_info"]["receives_snap"] = True
    data["financial_info"]["receives_ssi"] = True

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "co_fw.pdf")
        ok = fill_fee_waiver(data, "CO", out_pdf)
        assert ok is True
        assert os.path.exists(out_pdf)

        doc = pymupdf.open(out_pdf)
        assert len(doc) == 3

        # Page 1: Categorical benefits
        p1_widgets = _get_page_widgets(doc[0])
        assert p1_widgets.get("6.3") == "Yes"  # SSI
        assert p1_widgets.get("6.5") == "Yes"  # SNAP

        # Page 2: Section 8 Household table
        p2_widgets = _get_page_widgets(doc[1])
        assert p2_widgets.get("8A.1") == "Jane Doe"
        assert p2_widgets.get("8A.2") == "34"
        assert p2_widgets.get("8A.3") == "Spouse"
        assert p2_widgets.get("Group8A") == "Yes."

        assert p2_widgets.get("8B.1") == "Tommy Doe"
        assert p2_widgets.get("8B.2") == "8"
        assert p2_widgets.get("8B.3") == "Child"
        assert p2_widgets.get("Group8B") == "Yes."

        # Page 3: Section 10 Bank Name
        p3_widgets = _get_page_widgets(doc[2])
        assert p3_widgets.get("10A.3B") == "FirstBank"
