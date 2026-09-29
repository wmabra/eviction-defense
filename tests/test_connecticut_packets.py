"""
Tests for Connecticut (CT) eviction packet generation, verifying Form JD-HM-5
(Summary Process Answer), Form JD-CV-120 (Fee Waiver), and full packet bundling.
"""
import os
import sys
import copy
import tempfile
import fitz
from pathlib import Path

# Ensure app is in python path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.generate_test_packet import CT
from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver
from app.services.chat import build_system_prompt
from app.services.generator import generate_packet


def _get_page_widgets(page) -> dict[str, str]:
    """Extract widgets, returning mapping of field_name to string value."""
    res = {}
    for w in page.widgets():
        val = w.field_value
        if val not in ("", "Off", None, False) or w.field_name not in res:
            res[w.field_name] = str(val)
    return res


def test_connecticut_prompts():
    """Verify chat system prompt customization for Connecticut."""
    prompt = build_system_prompt("CT", "Hartford")

    # State identity and form names
    assert "Connecticut (CT)" in prompt
    assert "Housing Court / Superior Court" in prompt
    assert "Form JD-HM-5" in prompt
    assert "Form JD-CV-120" in prompt
    assert "TFA / Temporary Family Assistance" in prompt

    # Defenses list includes official JD-HM-5 defense keys
    assert "def_paid" in prompt
    assert "def_repairs" in prompt
    assert "def_retaliation" in prompt
    assert "def_corrected" in prompt

    # Dependents count only (no household member table)
    assert "total number of dependents" in prompt.lower()
    assert "do not ask for individual names, ages, or relationships" in prompt.lower()

    # Zero Colorado leakage
    assert "Colorado Courts E-Filing" not in prompt
    assert "Denver" not in prompt
    assert "Section 7e" not in prompt
    assert "what is the name of your bank" not in prompt.lower()
    assert "judge trial or a jury trial" not in prompt


def test_connecticut_answer_form_fill():
    """Verify Form JD-HM-5 answer form filling, denial of complaint, and certification."""
    data = copy.deepcopy(CT["data"])

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "ct_answer.pdf")
        ok = fill_answer_form(data, "CT", out_pdf)
        assert ok is True
        assert os.path.exists(out_pdf)

        doc = fitz.open(out_pdf)
        assert len(doc) == 1

        p1_widgets = _get_page_widgets(doc[0])

        # Caption
        assert "Nutmeg State Properties, LLC v. John Doe" in p1_widgets.get("form1[0].FRONT[0].CASE[0]", "")
        assert p1_widgets.get("form1[0].FRONT[0].DOCKETNO[0]") == "HFH-CV24-6012345"

        # Complaint denials: paragraphs 1-8 all Disagreed (val='2')
        for i in range(1, 9):
            assert p1_widgets.get(f"form1[0].FRONT[0].PARA{i}[1]") in ("2", "Yes", "true", "1")

        # Part 2 defenses:
        # Repairs / code violations checked (Boxes d and e)
        assert p1_widgets.get("form1[0].FRONT[0].NORENTDUE[0]") in ("1", "Yes", "true", "2")
        assert "heating system has been broken" in p1_widgets.get("form1[0].FRONT[0].CODEVIOLA[0]", "")
        assert p1_widgets.get("form1[0].FRONT[0].NOTIFIED[0]") in ("1", "Yes", "true", "2")
        assert p1_widgets.get("form1[0].FRONT[0].NOTE[0]") in ("1", "Yes", "true", "2")  # landlord notified

        # Disputed amount / unauthorized fees in Box k (Additional reasons)
        assert p1_widgets.get("form1[0].FRONT[0].ADDITIONALREASONS[0]") in ("1", "Yes", "true", "2")
        assert "unauthorized late fees" in p1_widgets.get("form1[0].FRONT[0].ADDINFO[0]", "")

        # Certification block at bottom
        assert p1_widgets.get("form1[0].FRONT[0].CERTNAME[0]") == "John Doe"
        assert p1_widgets.get("form1[0].FRONT[0].CERTMAIL[0]") == "238 Maple Avenue, Hartford, CT 06112"
        assert p1_widgets.get("form1[0].FRONT[0].CERTPHONE[0]") == "(860) 555-0171"
        assert "Nutmeg State Properties" in p1_widgets.get("form1[0].FRONT[0].CERTADDR[0]", "")
        assert p1_widgets.get("form1[0].FRONT[0].CERTDATESIGN[0]") != ""
        assert p1_widgets.get("form1[0].FRONT[0].CERTDATE[0]") != ""


def test_connecticut_additional_defenses():
    """Verify retaliation, pre-termination cure, and tender of rent on JD-HM-5."""
    data = copy.deepcopy(CT["data"])
    data["defenses"] = {
        "def_retaliation": {
            "checked": True,
            "explanation": "Eviction filed after tenant complained to health department.",
        },
        "def_corrected": {
            "checked": True,
            "explanation": "Cured the alleged unauthorized guest within 15 days.",
        },
        "def_attempted_pay": {
            "checked": True,
            "explanation": "Offered money order before notice to quit was served.",
        },
    }

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "ct_answer_defenses.pdf")
        ok = fill_answer_form(data, "CT", out_pdf)
        assert ok is True

        doc = fitz.open(out_pdf)
        p1_widgets = _get_page_widgets(doc[0])

        # Retaliation (Box f: EVICTION[0] and LANDLORD[0])
        assert p1_widgets.get("form1[0].FRONT[0].EVICTION[0]") in ("1", "Yes", "true", "2")
        assert p1_widgets.get("form1[0].FRONT[0].LANDLORD[0]") in ("1", "Yes", "true", "2")

        # Pre-termination notice cure (Box j: PRETERMINATION[0])
        assert p1_widgets.get("form1[0].FRONT[0].PRETERMINATION[0]") in ("1", "Yes", "true", "2")

        # Rent offered (Box b: RENTOFFERED[0])
        assert p1_widgets.get("form1[0].FRONT[0].RENTOFFERED[0]") in ("1", "Yes", "true", "2")


def test_connecticut_fee_waiver_fill():
    """Verify Form JD-CV-120 fee waiver schedule, expenses, income, assets, and court address."""
    data = copy.deepcopy(CT["data"])

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "ct_fw.pdf")
        ok = fill_fee_waiver(data, "CT", out_pdf)
        assert ok is True
        assert os.path.exists(out_pdf)

        doc = fitz.open(out_pdf)
        assert len(doc) == 3

        # Page 1: Caption, Case type, Court address, Income & Expenses
        p1_widgets = _get_page_widgets(doc[0])
        assert "Nutmeg State Properties" in p1_widgets.get("NAMECASE[0]", "")
        assert p1_widgets.get("DOCKETNO[0]") == "HFH-CV24-6012345"
        assert p1_widgets.get("topmostSubform[0].Page1[0].COURT[1]") == "2"  # Housing Session
        assert "80 Washington Street" in p1_widgets.get("topmostSubform[0].Page1[0].COURT[2]", "")
        assert p1_widgets.get("topmostSubform[0].Page1[0].NAMEAPP[0]") == "John Doe"
        assert "238 Maple Avenue" in p1_widgets.get("topmostSubform[0].Page1[0].ADDRAPP[0]", "")
        assert p1_widgets.get("topmostSubform[0].Page1[0].PHONE[0]") == "(860) 555-0171"
        assert p1_widgets.get("topmostSubform[0].Page1[0].TYPE[2]") == "4"  # Housing case
        assert p1_widgets.get("topmostSubform[0].Page1[0].FILING[0]") in ("Yes", "1", "true")

        # Dependents
        assert p1_widgets.get("DEPENDENTS") == "1"

        # Section 2: Income
        assert p1_widgets.get("GMI") == "$2,800.00"
        assert p1_widgets.get("NMI") == "$2,200.00"
        assert p1_widgets.get("TOTALMONTHLYINCOME") == "$2,200.00"  # Net (B) + Other (C)
        assert "SNAP" in p1_widgets.get("topmostSubform[0].Page1[0].COLUMN1[0].SOURCE[0]", "")

        # Section 3: Monthly Expenses (aligned to correct rows!)
        assert p1_widgets.get("ME1") == "$1,200.00"  # Rent/Mortgage
        assert p1_widgets.get("ME2") in ("", None, "0", "$0.00")  # Real Estate Taxes (tenant does not pay)
        assert p1_widgets.get("ME3") == "$200.00"    # Utilities
        assert p1_widgets.get("ME4") == "$420.00"    # Food
        assert p1_widgets.get("ME5") in ("", None, "0", "$0.00")  # Clothing
        assert p1_widgets.get("ME6") in ("", None, "0", "$0.00")  # Insurance
        assert p1_widgets.get("ME7") == "$100.00"    # Medical/Dental
        assert p1_widgets.get("ME8") == "$160.00"    # Transportation
        assert p1_widgets.get("ME9") in ("$0.00", "0", "")  # Childcare
        assert p1_widgets.get("TOTALME") == "$2,330.00"

        # Section 4: Assets
        assert p1_widgets.get("MVEV") == "$6,000.00"
        assert p1_widgets.get("MVLOANBAL") == "$2,500.00"
        assert p1_widgets.get("EQUITYMV") == "$3,500.00"
        assert p1_widgets.get("SAVINGS") == "$50.00"
        assert p1_widgets.get("CHECKING") == "$200.00"
        assert p1_widgets.get("CASH") == "$100.00"
        assert p1_widgets.get("TOTALASSETS") == "$3,850.00"

        # Section 5: Liabilities/Debts
        assert p1_widgets.get("topmostSubform[0].Page1[0].DEBTTYPE1[0]") == "Credit cards / personal loans"
        assert p1_widgets.get("DEBTOWED1") == "$2,500.00"
        assert p1_widgets.get("DEBTPAY1") == "$250.00"
        assert p1_widgets.get("DEBTOWEDTOTAL") == "$2,500.00"
        assert p1_widgets.get("DEBTPAYTOTAL") == "$250.00"

        # Page 2: Signature block
        p2_widgets = _get_page_widgets(doc[1])
        assert p2_widgets.get("topmostSubform[0].Page2[0].NAMESIGN[0]") == "John Doe"
        assert p2_widgets.get("topmostSubform[0].Page2[0].DATESIGN[0]") != ""
        assert p2_widgets.get("topmostSubform[0].Page2[0].DATESWORN[0]") in ("", None)


def test_connecticut_zero_income_support():
    """Verify that a zero-income applicant explains how supported on Page 2."""
    data = copy.deepcopy(CT["data"])
    data["financial_info"]["monthly_gross_income"] = 0.00
    data["financial_info"]["monthly_net_income"] = 0.00
    data["financial_info"]["employment_income"] = 0.00
    data["financial_info"]["other_income"] = 0.00

    with tempfile.TemporaryDirectory() as tmpdir:
        out_pdf = os.path.join(tmpdir, "ct_fw_zero.pdf")
        ok = fill_fee_waiver(data, "CT", out_pdf)
        assert ok is True

        doc = fitz.open(out_pdf)
        p2_widgets = _get_page_widgets(doc[1])
        assert "Assistance from family" in p2_widgets.get("topmostSubform[0].Page2[0].HOWSUPPORT[0]", "")


def test_connecticut_full_packet_generation():
    """Verify full 21-document packet generation for Connecticut."""
    data = copy.deepcopy(CT["data"])

    with tempfile.TemporaryDirectory() as tmpdir:
        paths = generate_packet(data, tmpdir)
        assert len(paths) >= 19

        # Add court answer and fee waiver
        court_pdf = os.path.join(tmpdir, "01_COURT_FORM_Answer_FILE_THIS.pdf")
        assert fill_answer_form(data, "CT", court_pdf) is True
        paths["court_form"] = court_pdf

        fee_waiver_pdf = os.path.join(tmpdir, "02_COURT_FORM_Fee_Waiver_FILE_THIS.pdf")
        assert fill_fee_waiver(data, "CT", fee_waiver_pdf) is True
        paths["fee_waiver"] = fee_waiver_pdf

        # All 21 files must exist and be non-empty
        assert len(paths) == 21
        for name, filepath in paths.items():
            assert os.path.exists(filepath), f"Missing file: {name}"
            assert os.path.getsize(filepath) > 0, f"Empty file: {name}"
