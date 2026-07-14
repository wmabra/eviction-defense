"""
PDF Document Generator — produces the complete self-help paperwork packet.

Generates up to 11 documents from confirmed customer data:
  01. Cover Page & Document Index
  02. Filing Checklist (state-specific)
  03. Court Hearing Checklist
  04. Hearing Script — What to Say in Court (personalized)
  05. Fee Waiver Instructions (state-specific)
  06. E-Filing Instructions (state-specific)
  07. Rental Assistance Resource Sheet (county-specific)
  --- Conditional documents (appended when applicable) ---
  08. Landlord Payment-Plan Letter
  09. Hardship / Extension Letter
  10. Motion to Determine Rent

Court answer form and fee waiver form are filled via form_filler.py
using each state's official court PDF for guaranteed court acceptance.
"""

import os
import logging
from datetime import date, datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, HRFlowable,
)
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)


def generate_packet(case_data: dict, output_dir: str) -> dict:
    """Generate all documents for a case.

    Args:
        case_data: Confirmed case profile with all fields
        output_dir: Directory to save generated PDFs

    Returns:
        dict with paths to each generated document
    """
    os.makedirs(output_dir, exist_ok=True)
    base = case_data

    paths = {}

    # 1. Official Court Answer Form — NOT generated here.
    #    The official form is filled via fill_answer_form() (fillable or overlay)
    #    using the state's actual court PDF. This ensures court acceptance.
    #    The generated answer form (below) is deprecated — it was the original
    #    FL-only approach before we had working overlay for the scanned form.
    #
    # OLD: _generate_answer_form(base, answer_path)
    # NEW: Use fill_answer_form(data, state, output_path) separately

    # Generate all supporting documents. Always-present docs use sequential
    # numbering. Conditional docs use higher numbers so there are never gaps.
    seq = 0  # will increment before each use

    # Always-present documents
    seq += 1
    emergency_path = os.path.join(output_dir, f"{seq:02d}_emergency_action_plan.pdf")
    _generate_emergency_action_plan(base, emergency_path)
    paths["emergency_action_plan"] = emergency_path

    seq += 1
    timeline_path = os.path.join(output_dir, f"{seq:02d}_eviction_timeline.pdf")
    _generate_eviction_timeline(base, timeline_path)
    paths["eviction_timeline"] = timeline_path

    seq += 1
    defenses_path = os.path.join(output_dir, f"{seq:02d}_defenses_explained.pdf")
    _generate_defenses_explained(base, defenses_path)
    paths["defenses_explained"] = defenses_path

    seq += 1
    evidence_path = os.path.join(output_dir, f"{seq:02d}_evidence_guide.pdf")
    _generate_evidence_guide(base, evidence_path)
    paths["evidence_guide"] = evidence_path

    seq += 1
    income_path = os.path.join(output_dir, f"{seq:02d}_income_expense_worksheet.pdf")
    _generate_income_expense_worksheet(base, income_path)
    paths["income_expense_worksheet"] = income_path

    seq += 1
    filing_path = os.path.join(output_dir, f"{seq:02d}_filing_checklist.pdf")
    _generate_filing_checklist(base, filing_path)
    paths["filing_checklist"] = filing_path

    seq += 1
    court_checklist_path = os.path.join(output_dir, f"{seq:02d}_court_checklist.pdf")
    _generate_court_checklist(base, court_checklist_path)
    paths["court_checklist"] = court_checklist_path

    seq += 1
    hearing_path = os.path.join(output_dir, f"{seq:02d}_hearing_script.pdf")
    _generate_hearing_script(base, hearing_path)
    paths["hearing_script"] = hearing_path

    # Fee Waiver form is NOT generated here — the actual court form is filled
    # separately by fill_fee_waiver() and included in the package as
    # 02_COURT_FORM_Fee_Waiver_FILE_THIS.pdf

    seq += 1
    rental_path = os.path.join(output_dir, f"{seq:02d}_rental_assistance.pdf")
    _generate_rental_assistance_sheet(base, rental_path)
    paths["rental_assistance"] = rental_path

    # Conditional documents
    cond_seq = seq

    defenses = base.get("defenses", {})

    # Demand letter — if tenant checked a repair-related defense
    repair_defenses = ["def_repairs", "def_landlord_breach", "def_failed_repair", "def_did_repairs"]
    if any(defenses.get(d, {}).get("checked") for d in repair_defenses if isinstance(defenses.get(d), dict)):
        cond_seq += 1
        demand_path = os.path.join(output_dir, f"{cond_seq:02d}_demand_letter.pdf")
        _generate_demand_letter(base, demand_path)
        paths["demand_letter"] = demand_path

    if defenses.get("def_amount", {}).get("checked"):
        cond_seq += 1
        mtr_path = os.path.join(output_dir, f"{cond_seq:02d}_motion_to_determine_rent.pdf")
        _generate_motion_to_determine_rent(base, mtr_path)
        paths["motion_to_determine_rent"] = mtr_path

    if base.get("preferences", {}).get("wants_payment_plan"):
        cond_seq += 1
        pplan_path = os.path.join(output_dir, f"{cond_seq:02d}_payment_plan_letter.pdf")
        _generate_payment_plan_letter(base, pplan_path)
        paths["payment_plan_letter"] = pplan_path

    if base.get("preferences", {}).get("needs_more_time"):
        cond_seq += 1
        hardship_path = os.path.join(output_dir, f"{cond_seq:02d}_hardship_letter.pdf")
        _generate_hardship_letter(base, hardship_path)
        paths["hardship_letter"] = hardship_path

    # Cover page — generated last so it knows all included documents
    cover_path = os.path.join(output_dir, "01_cover_page.pdf")
    _generate_cover_page(base, paths, cover_path)
    paths["cover_page"] = cover_path

    return paths


# ======================== FORM 1.947(b) ANSWER ========================

def _generate_answer_form(data: dict, output_path: str):
    """Generate the Florida Form 1.947(b) Answer — Residential Eviction."""
    doc = SimpleDocTemplate(
        output_path, pagesize=letter,
        topMargin=0.6*inch, bottomMargin=0.6*inch,
        leftMargin=0.75*inch, rightMargin=0.75*inch,
    )
    styles = _get_styles()
    elements = []
    S = styles  # shorthand

    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})

    # Caption
    caption_text = (
        f"IN THE COUNTY COURT, IN AND FOR {c.get('court_name', '_____ COUNTY')} COUNTY, FLORIDA\n"
        f"CASE NO.: {c.get('case_number', '_______________')}\n"
        f"DIVISION: _______________\n\n"
        f"{l.get('landlord_name', '_____________________________')}, Plaintiff(s),\n"
        f"vs.\n"
        f"{p.get('full_name', '_____________________________')}, Defendant(s).\n"
    )
    elements.append(Paragraph(caption_text, S["Caption"]))
    elements.append(HRFlowable(width="100%", thickness=1))
    elements.append(Spacer(1, 12))

    # Title
    elements.append(Paragraph("ANSWER – RESIDENTIAL EVICTION", S["Title"]))
    elements.append(Spacer(1, 12))

    # Section 1: Answer the complaint
    elements.append(Paragraph(
        "<b>1.</b> The defendant answers the complaint as follows: "
        "(Check <b>ONLY 1</b>, a. or b.)", S["Body"]
    ))
    elements.append(Spacer(1, 6))

    # Determine if they generally deny or admit
    defenses = data.get("defenses", {})
    checked_defenses = [k for k, v in defenses.items() if isinstance(v, dict) and v.get("checked")]
    generally_deny = len(checked_defenses) > 0  # If they have defenses, they generally deny

    if generally_deny:
        elements.append(Paragraph("☑ <b>a.</b> Defendant generally denies each statement of the complaint.", S["Body"]))
        elements.append(Paragraph("☐ <b>b.</b> Defendant admits that all the statements of the complaint are true EXCEPT:", S["Body"]))
    else:
        elements.append(Paragraph("☐ <b>a.</b> Defendant generally denies each statement of the complaint.", S["Body"]))
        elements.append(Paragraph("☑ <b>b.</b> Defendant admits that all the statements of the complaint are true EXCEPT:", S["Body"]))
        elements.append(Paragraph(
            "&nbsp;&nbsp;&nbsp;&nbsp;i. The following statement(s) in paragraph(s) _________ of the complaint is/are false.",
            S["Body"]
        ))

    elements.append(Spacer(1, 12))

    # Section 2: Rent deposit warning
    elements.append(Paragraph(
        '<b>2.</b> If you write down any defense other than payment of rent, then you must take '
        'one of the following steps:', S["Body"]
    ))
    elements.append(Paragraph(
        '&nbsp;&nbsp;<b>a.</b> If you agree with the landlord about the rent owed, then you must pay '
        'the rent owed into the court registry when you file this response.', S["Body"]
    ))
    elements.append(Paragraph(
        '&nbsp;&nbsp;<b>b.</b> If you disagree with the landlord about the rent owed for any reason, '
        'then you must check box 3(b) below and describe with detail why you disagree.', S["Body"]
    ))
    elements.append(Paragraph(
        '&nbsp;&nbsp;<b>c.</b> You <b>MUST</b> pay the clerk of court the rent each time it becomes due '
        'until the lawsuit is over. If you fail to follow these instructions, then you will lose your '
        'defenses. You will not have a hearing in your case and you may be evicted without a court date.',
        S["BodyWarning"]
    ))
    elements.append(Spacer(1, 12))

    # Section 3: Defenses
    elements.append(Paragraph(
        "<b>3.</b> The defendant sets forth the following defenses to the complaint: "
        "(Check ONLY the defenses that apply, and state brief facts to support each checked defense.)",
        S["Body"]
    ))
    elements.append(Spacer(1, 6))

    defense_items = [
        ("a", "The landlord did not make repairs, and I withheld my rent after sending written notice to the landlord.",
         "def_repairs", "(Attach a copy of the written notice to the landlord.)"),
        ("b", "I do not owe the total amount of rent or ongoing amount of rent the landlord claims I owe.",
         "def_amount", "(Motion to Determine Rent.)"),
        ("c", "I attempted/offered to pay all the rent due before the notice to pay rent expired, but the landlord did not accept the rent payment.",
         "def_attempted_pay", ""),
        ("d", "I paid the rent demanded by the landlord in the notice to pay rent.",
         "def_paid", ""),
        ("e", "The landlord waived, changed, or canceled the notice that required me to move out.",
         "def_waived", ""),
        ("f", "The landlord filed the eviction in retaliation against me.",
         "def_retaliation", ""),
        ("g", "The landlord filed the eviction in violation of the Federal Fair Housing Act and/or the Florida Fair Housing Act.",
         "def_fair_housing", ""),
        ("h", "The landlord accepted rent from me after sending me the notice to terminate.",
         "def_accepted_rent", ""),
        ("i", "I already corrected the violations claimed by the landlord on the notice to terminate.",
         "def_corrected", ""),
        ("j", "The landlord is not the owner of the property where I live.",
         "def_not_owner", ""),
        ("k", "I did not receive the notice to terminate or the notice was legally incorrect.",
         "def_bad_notice", ""),
        ("l", "Other defenses.",
         "def_other", ""),
    ]

    for letter_code, text, def_key, extra in defense_items:
        defense = defenses.get(def_key, {})
        checked = defense.get("checked", False) if isinstance(defense, dict) else False
        explanation = defense.get("explanation", "") if isinstance(defense, dict) else ""

        checkbox = "☑" if checked else "☐"
        extra_text = f" <i>{extra}</i>" if extra else ""
        elements.append(Paragraph(
            f"{checkbox} <b>{letter_code}.</b> {text}{extra_text}",
            S["Body"]
        ))
        if checked and explanation:
            elements.append(Paragraph(
                f'&nbsp;&nbsp;&nbsp;&nbsp;<i>Explanation:</i> {explanation}',
                S["BodySmall"]
            ))
        elements.append(Spacer(1, 4))

    elements.append(Spacer(1, 12))

    # Section 4: Jury trial notice
    elements.append(Paragraph("<b>4.</b> You have a constitutional right to request a trial by jury.", S["Body"]))
    for sub in ["a", "b", "c", "d"]:
        jury_texts = {
            "a": "You may have waived this right in your lease, so review it carefully before requesting a jury trial.",
            "b": "If you want a jury trial, you should request it in writing when you file your answer.",
            "c": "Jury trials are not simple to conduct. You will bear some responsibility in the process.",
            "d": "If you have questions about whether to request a jury trial, you should speak with an attorney.",
        }
        elements.append(Paragraph(f"&nbsp;&nbsp;<b>{sub}.</b> {jury_texts[sub]}", S["BodySmall"]))

    elements.append(Spacer(1, 12))

    # Section 5: Trial by judge or jury
    trial_by = data.get("preferences", {}).get("trial_by", "judge")
    judge_checked = "☑" if trial_by == "judge" else "☐"
    jury_checked = "☑" if trial_by == "jury" else "☐"

    elements.append(Paragraph("<b>5.</b> Select whether you want to request a jury trial:", S["Body"]))
    elements.append(Paragraph(f"{judge_checked} I want a <b>judge</b> to decide my case.", S["Body"]))
    elements.append(Paragraph(f"{jury_checked} I want a <b>jury</b> to decide my case.", S["Body"]))
    elements.append(Spacer(1, 12))

    # Signature block
    today = date.today().strftime("%B %d, %Y")
    elements.append(HRFlowable(width=3*inch, thickness=1, hAlign="LEFT"))
    elements.append(Paragraph(f"Signature: ______________________________", S["Body"]))
    elements.append(Paragraph(f"Printed Name: {p.get('full_name', '_____________________________')}", S["Body"]))
    elements.append(Paragraph(f"Date: {today}", S["Body"]))
    elements.append(Paragraph(f"Address: {p.get('property_address', '_____________________________')}", S["Body"]))
    elements.append(Paragraph(f"Telephone: {p.get('phone', '_____________________________')}", S["Body"]))
    elements.append(Paragraph(f"Email: {p.get('email', '_____________________________')}", S["Body"]))
    elements.append(Spacer(1, 12))

    # Certificate of Service
    elements.append(Paragraph("<b>CERTIFICATE OF SERVICE</b>", S["Body"]))
    elements.append(Paragraph(
        f"I CERTIFY that a copy has been furnished by mail / hand-delivery / portal e-service "
        f"on this {today}, to {l.get('landlord_name', 'the Plaintiff')}"
        f" at {l.get('landlord_address', '_____________________________')}.",
        S["BodySmall"]
    ))

    doc.build(elements)


# ======================== MOTION TO DETERMINE RENT ========================

def _generate_motion_to_determine_rent(data: dict, output_path: str):
    """Generate Motion to Determine Rent under §83.60(2)."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = _get_styles()
    elements = []
    S = styles

    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    r = data.get("rent_payment", {})

    caption = (
        f"IN THE COUNTY COURT, IN AND FOR {c.get('court_name', '_____ COUNTY')} COUNTY, FLORIDA\n"
        f"CASE NO.: {c.get('case_number', '_______________')}\n\n"
        f"{l.get('landlord_name', 'Plaintiff')},\n"
        f"vs.\n"
        f"{p.get('full_name', 'Defendant')},\n"
    )
    elements.append(Paragraph(caption, S["Caption"]))
    elements.append(HRFlowable(width="100%", thickness=1))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("DEFENDANT'S MOTION TO DETERMINE RENT", S["FormTitle"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph(
        f"Defendant, {p.get('full_name', '_________________')}, by and through this self-help filing, "
        f"respectfully requests this Court to determine the amount of rent to be deposited "
        f"into the Court Registry pursuant to Florida Statute §83.60(2).", S["Body"]
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("<b>FACTUAL BACKGROUND</b>", S["BodyBold"]))
    elements.append(Paragraph(
        f"1. Defendant resides at {p.get('property_address', '_________________')}, "
        f"{p.get('property_city', '')}, Florida.", S["Body"]
    ))
    elements.append(Paragraph(
        f"2. Plaintiff filed a complaint for eviction claiming ${c.get('complaint_amount_claimed', '0')} "
        f"in unpaid rent.", S["Body"]
    ))
    elements.append(Paragraph(
        f"3. Defendant believes the amount claimed is incorrect.", S["Body"]
    ))
    if r.get("why_disagree"):
        elements.append(Paragraph(
            f"4. Specifically: {r['why_disagree']}", S["Body"]
        ))
    elements.append(Paragraph(
        f"5. Defendant believes the correct amount owed is "
        f"${r.get('amount_tenant_believes_owed', 'an amount to be determined by the Court')}.", S["Body"]
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("<b>ARGUMENT</b>", S["BodyBold"]))
    elements.append(Paragraph(
        "Florida Statute §83.60(2) provides that when a tenant disputes the amount of rent "
        "alleged in the complaint, the Court shall determine the correct amount to be deposited "
        "into the Court Registry.", S["Body"]
    ))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("<b>CERTIFICATE OF SERVICE</b>", S["BodyBold"]))
    today = date.today().strftime("%B %d, %Y")
    elements.append(Paragraph(
        f"I HEREBY CERTIFY that a true and correct copy of the foregoing has been furnished "
        f"to {l.get('landlord_name', 'Plaintiff')} at {l.get('landlord_address', '_________________')} "
        f"on this {today}.", S["BodySmall"]
    ))
    elements.append(Spacer(1, 12))

    hr = HRFlowable(width=3*inch, thickness=1, hAlign="LEFT")
    elements.append(hr)
    elements.append(Paragraph(f"Signature: ______________________________", S["Body"]))
    elements.append(Paragraph(f"Date: {today}", S["Body"]))
    elements.append(Paragraph(f"{p.get('full_name', '_________________')}, Defendant", S["Body"]))
    elements.append(Paragraph(f"{p.get('phone', '')}", S["Body"]))
    elements.append(Paragraph(f"{p.get('email', '')}", S["Body"]))

    doc.build(elements)


# ======================== LETTERS (DOCX) ========================

def _generate_payment_plan_letter(data: dict, output_path: str):
    """Generate landlord payment-plan request letter as PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=1*inch, bottomMargin=1*inch,
                            leftMargin=1*inch, rightMargin=1*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    pref = data.get("preferences", {})
    today = date.today().strftime("%B %d, %Y")
    
    amount_claimed = c.get('complaint_amount_claimed', 0)
    plan_amount = pref.get('payment_plan_amount', '')
    if not plan_amount and amount_claimed:
        try:
            plan_amount = f"${float(amount_claimed) / 4:,.0f}"
        except:
            plan_amount = "$_____"
    
    elements.append(Paragraph(today, S["Body"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(l.get("landlord_name", "Landlord"), S["Body"]))
    elements.append(Paragraph(l.get("landlord_address", ""), S["Body"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"<b>RE:</b> Payment Plan Request — Property at {p.get('property_address', '')}<br/>"
        f"&nbsp;&nbsp;&nbsp;&nbsp;Case No: {c.get('case_number', '')}",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Dear {l.get('landlord_name', 'Landlord')},", S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"I am writing to request a payment plan to address the outstanding rent balance "
        f"of ${amount_claimed}. I am committed to fulfilling my obligations under the lease "
        f"and propose the following payment arrangement:",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Monthly payment:</b> {plan_amount}", S["Body"]))
    elements.append(Paragraph("<b>Payment due on:</b> The 1st day of each month", S["Body"]))
    elements.append(Paragraph(f"<b>Start date:</b> {date.today().strftime('%B 1, %Y')}", S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "I am requesting this arrangement due to temporary financial hardship. "
        "I will make every effort to adhere to this schedule.",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("Thank you for your consideration.", S["Body"]))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("Sincerely,", S["Body"]))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph(p.get("full_name", ""), S["Body"]))
    elements.append(Paragraph(p.get("phone", ""), S["BodySmall"]))
    elements.append(Paragraph(p.get("email", ""), S["BodySmall"]))
    
    doc.build(elements)


def _generate_hardship_letter(data: dict, output_path: str):
    """Generate hardship/extension letter as PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=1*inch, bottomMargin=1*inch,
                            leftMargin=1*inch, rightMargin=1*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    pref = data.get("preferences", {})
    today = date.today().strftime("%B %d, %Y")
    
    hardship_reason = pref.get('hardship_reason', 'temporary financial hardship')
    
    elements.append(Paragraph(today, S["Body"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(l.get("landlord_name", "Landlord"), S["Body"]))
    elements.append(Paragraph(l.get("landlord_address", ""), S["Body"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"<b>RE:</b> Hardship Request — {p.get('property_address', '')}<br/>"
        f"&nbsp;&nbsp;&nbsp;&nbsp;Case No: {c.get('case_number', '')}",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Dear {l.get('landlord_name', 'Landlord')},", S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "I am writing to respectfully request additional time regarding my tenancy "
        "due to the following circumstances:",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(hardship_reason, S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "I understand my obligations under the lease and I am not seeking to avoid them. "
        "I am simply requesting accommodation to make appropriate arrangements.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("Thank you for your understanding.", S["Body"]))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("Sincerely,", S["Body"]))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph(p.get("full_name", ""), S["Body"]))
    elements.append(Paragraph(p.get("phone", ""), S["BodySmall"]))
    elements.append(Paragraph(p.get("email", ""), S["BodySmall"]))
    
    doc.build(elements)


# ======================== CHECKLISTS ========================

def _generate_filing_checklist(data: dict, output_path: str):
    """Generate a state-specific step-by-step filing checklist PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = _get_styles()
    elements = []
    S = styles
    state = data.get("state", "FL").upper()
    p = data.get("personal_info", {})

    elements.append(Paragraph("FILING CHECKLIST", S["FormTitle"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        f"<b>For:</b> {p.get('full_name', 'Tenant')} — {p.get('county', 'your county')}, {state}",
        S["BodySmall"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Follow these steps to file your Answer with the court. "
        "Check off each item as you complete it.", S["Body"]
    ))
    elements.append(Spacer(1, 12))

    # State-specific deadlines
    STATE_DEADLINES = {
        "FL": "5 business days (excluding weekends and holidays)",
        "CA": "5 days if served in person, 15 days if served by substituted service",
        "TX": "14 days from the date you were served (or the Monday after if the 14th day falls on a weekend)",
        "IL": "5-10 days depending on the type of eviction (check your summons for the exact date)",
        "MI": "7 days from the date you were served",
        "NV": "7 days from the date you were served",
        "OR": "7 days from the date you were served",
        "MN": "7 days from the date you were served",
        "CO": "7 days from the date you were served",
        "CT": "2 days from the return date on your summons",
        "RI": "20 days from the date you were served",
        "SC": "10 days from the date you were served",
        "GA": "7 days from the date you were served",
        "LA": "5-10 days depending on the parish (check your summons)",
        "TN": "14 days from the date you were served",
        "AR": "5 days from the date you were served",
        "AZ": "5 days from the date you were served",
        "VA": "You must appear on the return date shown on your summons",
        "MA": "You must file your Answer on or before the return date listed on your summons",
        "NM": "10 days from the date you were served",
    }
    deadline = STATE_DEADLINES.get(state, "the deadline shown on your summons")

    steps = [
        ("☐ Step 1: Review Your Packet",
         "Read through all documents. Make sure your name, case number, and all information is correct."),
        ("☐ Step 2: Sign the Answer Form",
         "Sign and date your Answer form where indicated. Use blue or black ink."),
        ("☐ Step 3: Make Copies",
         "Make at least 3 copies of EVERY document in your packet. Keep one copy for yourself."),
        ("☐ Step 4: File with the Court Clerk",
         f"Take the original + 2 copies to the courthouse where your case was filed. "
         f"Ask the clerk to stamp all copies as 'Filed' and keep a stamped copy."),
        ("☐ Step 5: Check Filing Fee (or File Fee Waiver)",
         "Ask the clerk about the filing fee. If you cannot afford it, submit your "
         "fee waiver form (included in this packet) at the same time."),
        ("☐ Step 6: Serve the Landlord",
         "You must deliver a copy of your filed Answer to the landlord or their attorney. "
         "Keep proof of delivery (certified mail receipt, hand-delivery receipt, or email confirmation)."),
        ("☐ Step 7: Note Your Deadline",
         f"Your response deadline: {deadline}. Mark this date on your calendar."),
        ("☐ Step 8: Prepare for Hearing",
         "If a hearing is scheduled, bring all your documents, evidence, "
         "and your hearing script (included in this packet). Review it beforehand."),
        ("☐ Step 9: Attend All Court Dates",
         "Arrive 15 minutes early. If you miss a court date, the judge may enter "
         "a default judgment against you."),
        ("☐ Step 10: File Proof of Service",
         "After serving the landlord, file a Certificate of Service or Proof of Service "
         "with the court. The e-filing instructions in this packet explain how."),
    ]

    for title, desc in steps:
        elements.append(Paragraph(title, S["BodyBold"]))
        elements.append(Paragraph(desc, S["BodySmall"]))
        elements.append(Spacer(1, 6))

    doc.build(elements)


def _generate_court_checklist(data: dict, output_path: str):
    """Generate 'what to bring to court' checklist PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = _get_styles()
    elements = []
    S = styles

    elements.append(Paragraph("COURT HEARING CHECKLIST", S["FormTitle"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "What to bring with you to your eviction hearing:", S["Body"]
    ))
    elements.append(Spacer(1, 12))

    items = [
        "☐ This packet (your filed Answer and all supporting documents)",
        "☐ Your lease or rental agreement",
        "☐ Any rent receipts or proof of payment (bank statements, canceled checks)",
        "☐ Photos or videos of any repair issues (if applicable)",
        "☐ Any written communication with your landlord (emails, texts, letters)",
        "☐ Your 7-day repair notice (if you sent one)",
        "☐ Proof of rental assistance application (if applicable)",
        "☐ Photo ID",
        "☐ A pen and paper for taking notes",
        "☐ A list of the points you want to make to the judge",
        "☐ Any witnesses (if applicable)",
        "☐ Your phone (silenced) with important numbers saved",
    ]

    for item in items:
        elements.append(Paragraph(item, S["Body"]))
        elements.append(Spacer(1, 6))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>WHAT TO EXPECT AT THE HEARING:</b>", S["BodyBold"]))
    elements.append(Spacer(1, 6))

    expectations = [
        "Arrive early. Find the right courtroom.",
        "When your case is called, step forward.",
        "Address the judge as 'Your Honor.'",
        "Stay calm. Speak clearly. Stick to the facts.",
        "The landlord (or their lawyer) will speak first.",
        "When it's your turn, explain your defense briefly.",
        "Show the judge any evidence you brought.",
        "The judge may ask questions — answer honestly.",
        "The judge will make a decision or set another hearing date.",
    ]

    for exp in expectations:
        elements.append(Paragraph(f"• {exp}", S["BodySmall"]))

    doc.build(elements)


# ======================== HEARING SCRIPT ========================

def _generate_hearing_script(data: dict, output_path: str):
    """Generate a personalized hearing script based on the tenant's actual defenses."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    defenses = data.get("defenses", {})
    full_name = p.get('full_name', '[YOUR NAME]')
    
    elements.append(Paragraph("YOUR COURT HEARING SCRIPT", S["FormTitle"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"<b>Prepared for:</b> {full_name}<br/>"
        "This script helps you speak to the judge. You can bring this paper with you.",
        S["Body"]
    ))
    elements.append(Spacer(1, 14))
    
    # Gather checked defenses
    DEFENSE_LABELS = {
        "def_repairs": "The landlord failed to make necessary repairs despite being notified.",
        "def_amount": "I dispute the amount of rent the landlord claims I owe.",
        "def_attempted_pay": "I tried to pay the rent but the landlord refused to accept it.",
        "def_paid": "I have already paid the rent that the landlord claims is owed.",
        "def_waived": "The landlord waived or canceled the eviction notice.",
        "def_retaliation": "The landlord is evicting me in retaliation for exercising my rights.",
        "def_fair_housing": "The eviction violates fair housing laws (discrimination).",
        "def_accepted_rent": "The landlord accepted my rent after sending the eviction notice.",
        "def_corrected": "I already fixed the problem the landlord complained about.",
        "def_not_owner": "The person suing me is not the actual owner of the property.",
        "def_bad_notice": "I did not receive proper legal notice of the eviction.",
        "def_not_owed": "I do not owe the amount the landlord claims.",
        "def_landlord_breach": "The landlord broke the rental agreement.",
        "def_discrimination": "The eviction is discriminatory.",
        "def_other": "I have another legal defense to this eviction.",
    }
    
    checked = []
    for key, label in DEFENSE_LABELS.items():
        d = defenses.get(key, {})
        if isinstance(d, dict) and d.get("checked"):
            checked.append(label)
    
    # Build personalized defense statement
    if checked:
        defense_lines = ["<b>YOUR DEFENSES (tell the judge):</b>"]
        for i, defense in enumerate(checked, 1):
            defense_lines.append(f"{i}. {defense}")
        rent_dispute = any(d in ["def_amount", "def_not_owed"] for d in 
            [k for k, v in defenses.items() if isinstance(v, dict) and v.get("checked")])
    else:
        defense_lines = ["<b>YOUR DEFENSE:</b> Tell the judge briefly why you should not be evicted."]
        defense_lines.append("(Examples: Landlord refused repairs / Retaliation / Improper notice / Already paid)")
        rent_dispute = False
    
    script_lines = [
        ("<b>WHEN YOUR CASE IS CALLED:</b> Walk to the front of the courtroom.", False),
        (f"<b>You:</b> Good morning/afternoon, Your Honor. My name is {full_name}.", True),
        ("<b>Judge:</b> Do you have an attorney?", False),
        ("<b>You:</b> No, Your Honor. I am representing myself.", True),
        ("<b>Judge:</b> Have you filed your Answer?", False),
        ("<b>You:</b> Yes, Your Honor. Here is a copy. (hand judge a copy of your Answer)", True),
        ("<b>Judge:</b> Do you owe the rent?", False),
    ]
    
    if rent_dispute:
        script_lines.append(
            ("<b>You:</b> Your Honor, I dispute the amount claimed. I would like to explain why.", True)
        )
    else:
        script_lines.append(
            ("<b>You:</b> I have deposited the rent with the court, Your Honor.", True)
        )
    
    script_lines.append(("<b>EXPLAIN YOUR DEFENSE:</b> Now tell the judge:", False))
    for line in defense_lines:
        script_lines.append((line, False))
    script_lines.extend([
        ("<b>IF YOU NEED MORE TIME:</b>", False),
        ("<b>You:</b> Your Honor, I respectfully request additional time to resolve this matter.", True),
        ("<b>CLOSING:</b>", False),
        ("<b>You:</b> Thank you for hearing me, Your Honor.", True),
    ])
    
    for text, _ in script_lines:
        elements.append(Paragraph(text, S["Body"]))
        elements.append(Spacer(1, 6))
    
    elements.append(Spacer(1, 14))
    elements.append(Paragraph(
        "<b>TIPS:</b> Dress neatly. Turn off your phone. Do not interrupt. "
        "Bring all documents. Speak clearly and respectfully. "
        "If you don't understand a question, ask the judge to repeat it.",
        S["BodySmall"]
    ))
    
    doc.build(elements)


# ======================== FEE WAIVER ========================

def _generate_fee_waiver(data: dict, output_path: str):
    """Generate state-specific fee waiver instructions."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    county = p.get('county', 'your county')
    state = data.get("state", "FL").upper()
    
    # Complete state-specific fee waiver info for all 20 states
    WAIVER_INFO = {
        "VA": {"form": "Form CC-1414 — Petition for Proceeding Without Payment of Fees", "site": "www.vacourts.gov", "fee": "varies by court"},
        "SC": {"form": "Motion and Affidavit to Proceed In Forma Pauperis", "site": "www.sccourts.org", "fee": "varies by county"},
        "GA": {"form": "Poverty Affidavit (Affidavit of Indigence)", "site": "www.georgiacourts.gov", "fee": "varies by county"},
        "TX": {"form": "Statement of Inability to Afford Payment of Court Costs", "site": "www.txcourts.gov", "fee": "varies by court"},
        "IL": {"form": "Application for Waiver of Court Fees", "site": "www.illinoiscourts.gov", "fee": "varies by county"},
        "CT": {"form": "Application for Waiver of Fees (JD-CV-120)", "site": "www.jud.ct.gov", "fee": "varies by court"},
        "CO": {"form": "Motion to File Without Payment (JDF 205)", "site": "www.courts.state.co.us", "fee": "varies by court"},
        "LA": {"form": "Affidavit of Inability to Pay Costs (In Forma Pauperis)", "site": "www.lasc.org", "fee": "varies by parish"},
        "TN": {"form": "Uniform Civil Affidavit of Indigency", "site": "www.tncourts.gov", "fee": "varies by county"},
        "CA": {"form": "Form FW-001 — Request to Waive Court Fees", "site": "www.courts.ca.gov", "fee": "$240-$450"},
        "AR": {"form": "Affidavit of Indigency (In Forma Pauperis)", "site": "www.arcourts.gov", "fee": "varies by court"},
        "AZ": {"form": "Application for Deferral/Waiver of Court Fees", "site": "www.azcourts.gov", "fee": "varies by court"},
        "FL": {"form": "Form 12.902(e) — Affidavit of Indigency", "site": "www.flcourts.gov", "fee": "$295"},
        "MN": {"form": "In Forma Pauperis Affidavit (IFP102)", "site": "www.mncourts.gov", "fee": "varies by court"},
        "NV": {"form": "Application to Proceed In Forma Pauperis", "site": "www.civillawselfhelpcenter.org", "fee": "varies by court"},
        "OR": {"form": "Application for Deferral or Waiver of Fees", "site": "www.courts.oregon.gov", "fee": "varies by court"},
        "MI": {"form": "MC 20 — Fee Waiver Request", "site": "www.courts.michigan.gov", "fee": "varies by court"},
        "MA": {"form": "Affidavit of Indigency (Housing Court)", "site": "www.mass.gov/courts", "fee": "varies by court"},
        "NM": {"form": "Application for Free Process (In Forma Pauperis)", "site": "www.nmcourts.gov", "fee": "varies by court"},
        "RI": {"form": "Motion to Proceed In Forma Pauperis", "site": "www.courts.ri.gov", "fee": "varies by court"},
    }
    info = WAIVER_INFO.get(state, {"form": "your state's fee waiver form", "site": "your state court website", "fee": "varies"})
    
    elements.append(Paragraph("FEE WAIVER — FILE YOUR CASE FOR FREE", S["FormTitle"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>For:</b> {county}, {state}", S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"If you cannot afford the court filing fee, you can ask the court to waive it. "
        f"This is called filing \"In Forma Pauperis\" or an Affidavit of Indigency.",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>YOUR STATE USES:</b> {info['form']}", S["BodyBold"]))
    elements.append(Paragraph(f"Download from: {info['site']}", S["BodySmall"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>HOW TO FILE:</b>", S["BodyBold"]))
    for step in [
        f"1. A fillable fee waiver form is included in this packet. Review it and fill in any missing information.",
        "2. You will need to provide your income, expenses, assets, and number of dependents",
        "3. Sign the form in front of the court clerk (they notarize for free) or any notary public",
        f"4. Submit the fee waiver ALONG with your Answer form BEFORE the deadline",
        f"5. The judge reviews your financial situation — if approved, you pay $0 instead of {info['fee']}",
    ]:
        elements.append(Paragraph(step, S["Body"]))
        elements.append(Spacer(1, 3))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "<b>WHO QUALIFIES:</b> You receive public benefits (SNAP, Medicaid, SSI) OR your income "
        "is below 200% of federal poverty level OR paying the fee would cause financial hardship.",
        S["BodySmall"]))
    elements.append(Paragraph(
        "<b>IMPORTANT:</b> File the fee waiver AND your Answer together BEFORE the deadline. "
        "Even if the waiver is denied, you must still file on time.",
        S["BodyWarning"]))
    
    doc.build(elements)

# ======================== RENTAL ASSISTANCE ========================

def _generate_rental_assistance_sheet(data: dict, output_path: str):
    """Generate county-specific rental assistance resources as PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    state = data.get("state", "FL").upper()
    county = data.get("personal_info", {}).get("county", "your county")
    full_name = data.get("personal_info", {}).get("full_name", "Tenant")

    # Load verified phone numbers from state resource JSON
    import json as _json
    resource_json = os.path.join(os.path.dirname(__file__), f"{state.lower()}_resources.json")
    region_phones = {}
    statewide_phones = {
        "HUD": "1-800-569-4287",
        "United Way": "2-1-1",
        "211": "2-1-1",
    }
    if os.path.exists(resource_json):
        try:
            with open(resource_json) as f:
                state_data = _json.load(f)
            if "statewide" in state_data:
                statewide_phones.update(state_data["statewide"])
            counties = state_data.get("counties", {})
            regions = state_data.get("regions", {})
            county_info = counties.get(county, {})
            region = county_info.get("_region", "")
            if region and region in regions:
                region_phones = {k: v for k, v in regions[region].items() if not k.startswith("_")}
        except Exception as e:
            logger.warning(f"Could not load resource JSON: {e}")

    # Also try Excel database
    db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "databases")
    db_resources = []
    db_files = {
        "FL": "Florida_Eviction_Support_Verified_Resource_Database_200.xlsx",
        "AZ": "Arizona_Eviction_Support_Database_Framework_200.xlsx",
        "AR": "Arkansas_Eviction_Support_Database_Framework_200.xlsx",
        "CA": "California_Eviction_Support_Database_Framework_200.xlsx",
        "CO": "Colorado_Eviction_Support_Database_Framework_200.xlsx",
        "CT": "Connecticut_Eviction_Support_Database_Framework_200.xlsx",
        "GA": "Georgia_Eviction_Support_Database_Framework_200.xlsx",
        "IL": "Illinois_Eviction_Support_Database_Framework_200.xlsx",
        "LA": "Louisiana_Eviction_Support_Database_Framework_200.xlsx",
        "MI": "Michigan_Eviction_Support_Database_Framework_200.xlsx",
        "NV": "Nevada_Eviction_Support_Database_Framework_200.xlsx",
        "NM": "New_Mexico_Eviction_Support_Database_Framework_200.xlsx",
        "RI": "Rhode_Island_Eviction_Support_Database_Framework_200.xlsx",
        "TN": "Tennessee_Eviction_Support_Database_Framework_200.xlsx",
        "TX": "Texas_Eviction_Support_Database_Framework_200.xlsx",
        "VA": "Virginia_Eviction_Support_Database_Framework_200.xlsx",
    }
    db_file = db_files.get(state)
    if db_file:
        db_path = os.path.join(db_dir, db_file)
        if os.path.exists(db_path):
            try:
                import openpyxl
                wb = openpyxl.load_workbook(db_path)
                ws = wb['Verified Resources'] if 'Verified Resources' in wb.sheetnames else wb.active
                header_row = 1
                for r in range(1, min(6, ws.max_row + 1)):
                    for c in range(1, ws.max_column + 1):
                        if str(ws.cell(r, c).value or '').strip() == 'Organization':
                            header_row = r
                            break
                    if header_row > 1:
                        break
                col_map = {}
                for c in range(1, ws.max_column + 1):
                    hdr = str(ws.cell(header_row, c).value or '').strip().lower()
                    if 'county' in hdr or 'city' in hdr:
                        col_map['county'] = c
                    elif 'category' in hdr:
                        col_map['category'] = c
                    elif 'organization' in hdr:
                        col_map['organization'] = c
                    elif 'program' in hdr or 'service' in hdr:
                        col_map['program'] = c
                    elif 'website' in hdr:
                        col_map['website'] = c
                    elif 'phone' in hdr:
                        col_map['phone'] = c
                    elif 'eligibility' in hdr:
                        col_map['eligibility'] = c
                for row in range(header_row + 1, ws.max_row + 1):
                    r_county = str(ws.cell(row, col_map.get('county', 1)).value or "").strip()
                    if r_county.lower() == county.lower():
                        db_resources.append({
                            "category": str(ws.cell(row, col_map.get('category', 2)).value or ""),
                            "organization": str(ws.cell(row, col_map.get('organization', 3)).value or ""),
                            "website": str(ws.cell(row, col_map.get('website', 5)).value or ""),
                            "phone": str(ws.cell(row, col_map.get('phone', 6)).value or ""),
                        })
                wb.close()
            except Exception as e:
                logger.warning(f"Could not load resource database: {e}")

    # Clean up placeholder text in organization names
    PLACEHOLDER_SUFFIXES = [
        " — Area-specific resource slot / local program lookup",
        " — County-specific resource slot / local program lookup",
        " — Market-specific resource slot / local program lookup",
    ]
    for r in db_resources:
        for suffix in PLACEHOLDER_SUFFIXES:
            if r["organization"].endswith(suffix):
                r["organization"] = r["organization"][: -len(suffix)]
                break

    # Substitute placeholder phones from verified JSON
    placeholder_phones = {"Research / verify", "Research/verify", "N/A", "None", "See website", "Find local office", ""}
    all_phones = {**statewide_phones, **region_phones}
    for r in db_resources:
        phone = r.get("phone", "").strip()
        if phone in placeholder_phones:
            search = (r.get("category", "") + " " + r.get("organization", "")).lower()
            for keyword, num in all_phones.items():
                if keyword.lower() in search:
                    r["phone"] = num
                    break

    # Build PDF
    elements.append(Paragraph("RENTAL ASSISTANCE RESOURCES", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<b>Prepared for:</b> {full_name}<br/>"
        f"<b>County:</b> {county}, {state}",
        S["BodySmall"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "Contact these organizations as soon as possible — funds are limited "
        "and programs close when money runs out.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))

    if db_resources or region_phones:
        elements.append(Paragraph(f"<b>Local Resources — {county} County</b>", S["BodyBold"]))
        elements.append(Spacer(1, 8))

        if db_resources:
            from collections import defaultdict as _dd
            by_cat = _dd(list)
            for r in db_resources:
                by_cat[r["category"]].append(r)
            for cat, items in sorted(by_cat.items()):
                elements.append(Paragraph(f"<b>{cat}</b>", S["BodyBold"]))
                for item in items:
                    org = item["organization"]
                    phone = item.get("phone", "").strip()
                    web = item.get("website", "").strip()
                    if phone in placeholder_phones:
                        phone = ""
                    if web in ("None", "N/A", ""):
                        web = ""
                    line = f"• {org}"
                    if phone:
                        line += f" — {phone}"
                    elements.append(Paragraph(line, S["Body"]))
                    if web:
                        elements.append(Paragraph(f"&nbsp;&nbsp;{web}", S["BodySmall"]))
                    elements.append(Spacer(1, 3))
                elements.append(Spacer(1, 4))

        if region_phones:
            elements.append(Spacer(1, 4))
            elements.append(Paragraph("<b>Key Contacts</b>", S["BodyBold"]))
            for name, phone in sorted(region_phones.items()):
                elements.append(Paragraph(f"• {name}: {phone}", S["Body"]))
    else:
        elements.append(Paragraph(
            "<b>How to Find Local Help:</b>", S["BodyBold"]))
        elements.append(Paragraph(
            "• Dial <b>211</b> from any phone — United Way's free referral service for "
            "rent, utility, food, and emergency assistance.", S["Body"]))
        elements.append(Paragraph(
            "• Visit your county's official website and search for 'rental assistance' "
            "or 'housing programs.'", S["Body"]))
        elements.append(Paragraph(
            "• Contact your local Legal Aid office — search online for '[your county] legal aid'.",
            S["Body"]))

    # Statewide resources
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("<b>Statewide & National Resources</b>", S["BodyBold"]))
    for name, phone in sorted(statewide_phones.items()):
        if phone != "2-1-1":
            elements.append(Paragraph(f"• {name}: {phone}", S["Body"]))
        else:
            elements.append(Paragraph(f"• {name}: Dial 211 for free local referrals", S["Body"]))
    elements.append(Paragraph("• HUD Housing Counseling: 1-800-569-4287 or hud.gov/counseling", S["Body"]))
    elements.append(Paragraph("• Legal Services Corporation: lsc.gov/find-legal-aid", S["Body"]))

    # Tips
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("<b>Tips for Applying</b>", S["BodyBold"]))
    for tip in [
        "Apply as soon as possible — funds are limited and programs close when money runs out.",
        "Have these documents ready: lease, eviction notice/court papers, photo ID, proof of income.",
        "Many programs pay back rent directly to the landlord — ask about this option.",
        "If you have a pending application, tell the judge at your eviction hearing.",
        "Some programs require landlord cooperation — contact your landlord early.",
        "Keep copies of all applications, emails, and reference numbers.",
    ]:
        elements.append(Paragraph(f"• {tip}", S["BodySmall"]))
        elements.append(Spacer(1, 2))

    doc.build(elements)


# ======================== COVER PAGE ========================

# ======================== COVER PAGE ========================

def _generate_emergency_action_plan(data: dict, output_path: str):
    """Generate 'You Just Got Served' emergency action plan."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    c = data.get("case_details", {})

    elements.append(Paragraph("EMERGENCY ACTION PLAN — DO THIS TODAY", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<b>For:</b> {p.get('full_name', 'Tenant')}<br/>"
        f"<b>Your deadline is shown on your summons.</b> Do not wait.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))

    # Action steps
    steps = [
        ("IMMEDIATELY — Next 24 Hours", [
            "Find your eviction summons. Look for the DEADLINE DATE and CASE NUMBER.",
            "Write the deadline on your calendar. Set a phone alarm 2 days BEFORE it.",
            "Read this entire packet. You will need to understand every document.",
            "If you can, call a friend or family member. You do not have to do this alone.",
        ]),
        ("NEXT — Within 1-2 Days", [
            "Fill out and SIGN your Answer form (separate PDF). Use blue or black ink.",
            "Complete your fee waiver form if you cannot afford the filing fee.",
            "Make 3 copies of EVERYTHING. The court clerk keeps the original.",
        ]),
        ("FILE — Before Your Deadline", [
            "Go to the courthouse in person OR e-file online (see E-Filing Instructions).",
            "Bring: signed Answer form, fee waiver form, copies of everything, photo ID.",
            "Ask the clerk to stamp your copies as FILED. Keep one for yourself.",
            "If filing by mail, use certified mail with return receipt.",
        ]),
        ("AFTER FILING — Serve the Landlord", [
            "Deliver a filed copy to your landlord or their attorney.",
            "Do this by certified mail, hand delivery, or email (with read receipt).",
            "Keep PROOF — mail receipt, delivery confirmation, or email screenshot.",
        ]),
        ("PREPARE FOR COURT", [
            "Read the Defenses Explained document to understand your legal options.",
            "Read the Evidence Guide and start gathering evidence TODAY.",
            "Review the Hearing Script. Practice saying it out loud.",
            "Call the rental assistance numbers in this packet. Apply for help immediately.",
        ]),
    ]

    for title, items in steps:
        elements.append(Paragraph(f"<b>{title}</b>", S["BodyBold"]))
        for item in items:
            elements.append(Paragraph(f"☐ {item}", S["Body"]))
        elements.append(Spacer(1, 8))

    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "<b>IF YOU MISS YOUR DEADLINE:</b> The judge may enter a default judgment "
        "against you and you could be evicted without a hearing. THIS IS THE MOST "
        "IMPORTANT THING. File your answer on time.",
        S["BodyWarning"]
    ))

    doc.build(elements)


def _generate_eviction_timeline(data: dict, output_path: str):
    """Generate state-specific eviction process timeline."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    state = data.get("state", "FL").upper()
    p = data.get("personal_info", {})

    # State-specific timeline data
    TIMELINES = {
        "FL": [
            ("1. Notice to Pay or Quit", "3-15 days", "Landlord gives you written notice. You have this many days to pay or move out."),
            ("2. Eviction Complaint Filed", "After notice expires", "Landlord files complaint with the court. You will be served with a summons."),
            ("3. File Your Answer", "5 business days", "YOU ARE HERE. You must file a written response within 5 business days of being served."),
            ("4. Rent Deposit to Court Registry", "Same as answer", "If you raise any defense, you must deposit rent with the court clerk."),
            ("5. Hearing / Trial", "Usually 2-4 weeks", "Judge hears both sides. Bring all evidence. Decision may be same day."),
            ("6. Judgment", "Day of hearing", "If you lose, the judge issues a Final Judgment for Eviction."),
            ("7. Writ of Possession", "24-48 hours after judgment", "Sheriff posts a 24-hour notice on your door. You must vacate immediately."),
        ],
        "TX": [
            ("1. Notice to Vacate", "3-30 days", "Landlord gives you written notice. Timeline depends on lease type."),
            ("2. Eviction Suit Filed", "After notice expires", "Landlord files in Justice Court. You receive a citation with court date."),
            ("3. File Your Answer", "By court date", "YOU ARE HERE. File your answer before the hearing. You can file the morning of."),
            ("4. Trial", "10-21 days after filing", "Judge hears case. Both sides present evidence. You can appeal within 5 days."),
            ("5. Judgment", "Day of trial", "If you lose, judge signs judgment. You have 5 days to appeal or vacate."),
            ("6. Writ of Possession", "6+ days after judgment", "Constable posts notice. You must vacate. Only constable can remove you."),
        ],
        "CA": [
            ("1. Notice", "3-60 days", "Landlord serves notice (3-day pay or quit, 30/60-day no-fault)."),
            ("2. Summons & Complaint", "After notice", "You are served with court papers (Unlawful Detainer)."),
            ("3. File Answer", "5 days", "YOU ARE HERE. 5 days if served in person, 15 days if substituted service."),
            ("4. Discovery & Settlement", "1-3 weeks", "Parties exchange evidence. Settlement discussions possible."),
            ("5. Trial", "20 days after request", "Judge or jury trial. Most cases settle before this point."),
            ("6. Judgment & Lockout", "5 days after judgment", "Sheriff serves 5-day notice. Lockout occurs after notice expires."),
        ],
        "GA": [
            ("1. Notice", "Varies", "Landlord serves demand for possession (immediate) or pay-or-quit notice."),
            ("2. Dispossessory Filed", "After notice", "Landlord files dispossessory warrant. You are served with summons."),
            ("3. File Answer", "7 days", "YOU ARE HERE. Answer must be filed within 7 days of service."),
            ("4. Trial", "Within 7-14 days", "Judge hears both sides. You can request a jury trial."),
            ("5. Judgment & Appeal", "Day of trial", "You have 7 days to appeal. You may need to pay rent into court registry."),
            ("6. Writ of Possession", "7 days after judgment", "Sheriff executes eviction."),
        ],
        "IL": [
            ("1. Notice", "5-30 days", "Landlord serves written notice (5-day, 10-day, or 30-day depending on reason)."),
            ("2. Complaint Filed", "After notice", "Landlord files eviction complaint. You are served with summons."),
            ("3. File Appearance & Answer", "By return date", "YOU ARE HERE. You must appear and file answer by the return date on summons."),
            ("4. Trial", "Within 14 days", "Judge hears both sides. Illinois has a right-to-counsel program in some counties."),
            ("5. Judgment", "Day of trial", "If you lose, the judge issues an eviction order."),
            ("6. Enforcement", "Varies", "Sheriff serves eviction order. You typically have a few days to vacate."),
        ],
        "MI": [
            ("1. Notice to Quit", "7-30 days", "Landlord serves written notice (7 days for nonpayment, 30 days for other reasons)."),
            ("2. Summons & Complaint", "After notice", "Landlord files complaint. Court issues summons with hearing date."),
            ("3. File Answer", "By hearing date", "YOU ARE HERE. File your answer before or at the first hearing."),
            ("4. First Hearing / Pretrial", "~10 days after filing", "Initial hearing. Judge may set trial date or encourage settlement."),
            ("5. Trial", "1-2 weeks after pretrial", "Both sides present evidence. Judge issues ruling."),
            ("6. Judgment & Eviction", "10 days after judgment", "You have 10 days to vacate or appeal. Court order enforced by bailiff."),
        ],
        "VA": [
            ("1. Notice", "5-30 days", "Landlord serves pay-or-quit (5 days) or termination notice (30 days)."),
            ("2. Summons for Unlawful Detainer", "After notice", "You are served with court papers including a return date."),
            ("3. File Grounds of Defense", "By return date", "YOU ARE HERE. You must appear on the return date and file DC-442 Grounds of Defense."),
            ("4. Trial", "Return date or later", "Judge hears case. VA courts move quickly — often heard on the first appearance."),
            ("5. Judgment", "Day of trial", "If you lose, judge issues judgment. You have 10 days to appeal."),
            ("6. Writ of Possession", "10+ days after judgment", "Sheriff posts notice and executes eviction."),
        ],
        "MA": [
            ("1. Notice to Quit", "14-30 days", "Landlord serves notice to quit. Must be 14 days for nonpayment, 30 days for no-fault."),
            ("2. Summons & Complaint", "After notice", "Landlord files in Housing Court or District Court. You receive summons."),
            ("3. File Answer", "By return date", "YOU ARE HERE. File your answer. MA has a right to counsel program."),
            ("4. Mediation", "Before trial", "Many MA courts require mediation before trial. Opportunity to settle."),
            ("5. Trial", "1-4 weeks", "Judge hears both sides. You may qualify for free legal representation."),
            ("6. Judgment & Execution", "Varies", "If you lose, judge issues execution. Stay of execution may be available."),
        ],
        "CO": [
            ("1. Demand for Possession", "3-10 days", "Landlord serves written demand (3 days for nonpayment, 10 for lease violation)."),
            ("2. Summons in Forcible Entry", "After demand", "Landlord files complaint. You receive summons with court date."),
            ("3. File Answer", "By court date", "YOU ARE HERE. File answer before or at the return date on the summons."),
            ("4. Trial", "On return date", "Quick hearing. Judge hears both sides. Colorado courts move fast."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for possession. You may have 48 hours to vacate."),
            ("6. Eviction", "48 hours after judgment", "Sheriff can enforce eviction very quickly in Colorado."),
        ],
        "AZ": [
            ("1. Notice", "5-30 days", "Landlord serves written notice (5 days for nonpayment, 10 for material breach, 30 for no-fault)."),
            ("2. Eviction Complaint", "After notice", "Landlord files complaint. You are served. Your deadline depends on service method."),
            ("3. File Answer", "5-10 days", "YOU ARE HERE. 5 days if served in person, 10 days if posted on door."),
            ("4. Trial", "Within 3-10 days", "Quick hearing. Judge hears both sides. Arizona courts process evictions rapidly."),
            ("5. Judgment", "Day of trial", "If you lose, the judge issues judgment immediately."),
            ("6. Writ of Restitution", "5 days after judgment", "Constable posts 24-hour notice and executes eviction."),
        ],
        "TN": [
            ("1. Notice", "14-30 days", "Landlord serves written notice (14 days for nonpayment, 30 days for no-fault)."),
            ("2. Detainer Warrant", "After notice", "Landlord files detainer warrant. You receive summons."),
            ("3. File Answer / Sworn Denial", "By court date", "YOU ARE HERE. File sworn denial before hearing. You may need to notarize it."),
            ("4. Trial", "On court date", "Judge hears both sides. Tennessee courts move very quickly."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for possession. You have 10 days to appeal."),
            ("6. Writ of Possession", "10 days after judgment", "Sheriff executes eviction after appeal period expires."),
        ],
        "OR": [
            ("1. Notice", "72 hours - 30 days", "Landlord serves notice (72 hours for nonpayment, 30 days for no-fault after first year)."),
            ("2. Complaint (FED)", "After notice", "Landlord files Forcible Entry and Detainer. You receive summons."),
            ("3. File Answer / Appear", "By first hearing", "YOU ARE HERE. First appearance is usually within 7 days. File answer there."),
            ("4. Trial", "Within 15 days", "Judge hears case. Oregon has strong tenant protections and mediation programs."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for possession."),
            ("6. Notice of Restitution", "Varies", "Sheriff posts notice. You may be able to request additional time."),
        ],
        "NV": [
            ("1. Notice", "5-7 days", "Landlord serves eviction notice (5-day pay or quit, or 7-day no cause)."),
            ("2. Summary Eviction Complaint", "After notice", "Landlord files complaint. You receive summons. NV is a summary eviction state."),
            ("3. File Answer", "7 days", "YOU ARE HERE. You MUST file answer within 7 days. No exceptions."),
            ("4. Trial", "Within 10 days", "Quick trial. Judge hears both sides."),
            ("5. Judgment & Eviction", "Day of trial", "If you lose, eviction order issued immediately. Constable may enforce within 24-48 hours."),
        ],
        "MN": [
            ("1. Notice", "14-30 days", "Landlord serves written notice (14 days for nonpayment, 30 days to terminate no-fault)."),
            ("2. Eviction Complaint", "After notice", "Landlord files complaint. You receive summons with court date."),
            ("3. File Answer", "By court date", "YOU ARE HERE. File answer. Minnesota provides interpreters and help resources."),
            ("4. Trial", "On court date", "Judge hears both sides. MN courts emphasize housing stability."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for restitution of premises."),
            ("6. Writ of Recovery", "7+ days after judgment", "Sheriff executes eviction. You may request a stay in some circumstances."),
        ],
        "NM": [
            ("1. Notice", "3-30 days", "Landlord serves notice (3 days for nonpayment, 7 for lease violation, 30 for month-to-month)."),
            ("2. Petition for Restitution", "After notice", "Landlord files in Metropolitan or Magistrate Court. You receive summons."),
            ("3. File Answer", "3-10 days", "YOU ARE HERE. File your answer. Timeline depends on court."),
            ("4. Trial", "Within 7-14 days", "Judge hears both sides. Mediation may be offered."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for restitution. You have 3 working days to appeal."),
            ("6. Writ of Restitution", "3+ days after judgment", "Sheriff posts 24-hour notice and executes eviction."),
        ],
        "CT": [
            ("1. Notice to Quit", "3-5 days", "Landlord serves notice to quit (very short timeline in CT)."),
            ("2. Summons & Complaint", "After notice", "Landlord files in Housing Court. You receive summons with return date."),
            ("3. File Answer / Appear", "By return date", "YOU ARE HERE. Return date is typically within 7-10 days. You MUST appear."),
            ("4. Trial", "Within 30 days", "Housing Court judge hears case. CT has strong tenant protections and mediation."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for possession. You may request a stay of execution."),
            ("6. Execution", "5+ days after judgment", "State marshal executes eviction. Stay may give you additional time."),
        ],
        "SC": [
            ("1. Notice", "5-30 days", "Landlord serves written notice (5 days for nonpayment, 30 days for month-to-month)."),
            ("2. Application for Ejectment", "After notice", "Landlord files in Magistrate Court. You receive rule to show cause."),
            ("3. File Answer", "10 days", "YOU ARE HERE. Answer must be filed within 10 days of service."),
            ("4. Trial", "Within 10-30 days", "Magistrate judge hears case. Bring all evidence."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for ejectment. You have 5 days to appeal."),
            ("6. Writ of Ejectment", "5+ days after judgment", "Sheriff executes eviction after appeal period."),
        ],
        "AR": [
            ("1. Notice", "3-14 days", "Landlord serves notice (3 days for nonpayment, 14 days for no-fault)."),
            ("2. Unlawful Detainer Complaint", "After notice", "Landlord files complaint. You receive summons."),
            ("3. File Answer", "5 days", "YOU ARE HERE. 5 days to file a written objection/answer. AR is fast."),
            ("4. Trial", "Within 5-10 days", "Quick hearing. Judge or jury trial possible."),
            ("5. Judgment", "Day of trial", "If you lose, writ of possession issued. No automatic appeal period in AR."),
            ("6. Writ of Possession", "Immediately", "Sheriff can execute eviction very quickly after judgment."),
        ],
        "LA": [
            ("1. Notice to Vacate", "5-30 days", "Landlord serves written notice (5 days for nonpayment, 10 for lease violation, 30 for no-fault)."),
            ("2. Rule for Possession", "After notice", "Landlord files rule for possession. You receive citation with court date."),
            ("3. File Answer", "By court date", "YOU ARE HERE. Louisiana is a civil law state — procedures differ from other states."),
            ("4. Trial", "On court date", "Judge hears both sides. LA courts move quickly on evictions."),
            ("5. Judgment", "Day of trial", "If you lose, judge issues judgment of eviction. You have 24 hours to vacate in some parishes."),
            ("6. Eviction", "24-72 hours", "Constable or sheriff executes eviction. LA has very short post-judgment timelines."),
        ],
        "RI": [
            ("1. Notice", "5-30 days", "Landlord serves written notice (5 days for nonpayment, 20 for lease violation, 30 for month-to-month)."),
            ("2. Eviction Complaint", "After notice", "Landlord files in District Court. You receive summons."),
            ("3. File Answer", "20 days", "YOU ARE HERE. 20 days to file your answer. Longer than most states."),
            ("4. Trial", "Within 30 days", "District Court judge hears case. Mediation may be available."),
            ("5. Judgment", "Day of trial", "If you lose, judgment for possession. You may request a stay."),
            ("6. Execution", "Varies", "Sheriff executes eviction. Court may grant additional time to vacate."),
        ],
    }

    DEFAULT_TIMELINE = [
        ("1. Notice from Landlord", "Varies", "Landlord gives you written notice to pay rent or vacate."),
        ("2. Eviction Filed & Summons Served", "After notice", "Landlord files complaint. You receive a summons with your deadline."),
        ("3. File Your Answer", "Check your summons", "YOU ARE HERE. File your written response by the deadline on your summons."),
        ("4. Court Hearing", "Usually 2-4 weeks", "Judge hears both sides. Bring all documents and evidence."),
        ("5. Judgment", "Day of hearing or later", "Judge makes a decision. You may have the right to appeal (check your state)."),
        ("6. Eviction / Lockout", "Days to weeks after judgment", "If you lose, law enforcement carries out the eviction. You will receive notice."),
    ]

    timeline = TIMELINES.get(state, DEFAULT_TIMELINE)

    elements.append(Paragraph(f"EVICTION PROCESS — {state}", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<b>For:</b> {p.get('full_name', 'Tenant')}<br/>"
        "Understanding the process reduces fear and helps you prepare. "
        "This is a general timeline — your specific dates are on your summons.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))

    for title, time, desc in timeline:
        elements.append(Paragraph(f"<b>{title}</b> &nbsp; <i>({time})</i>", S["BodyBold"]))
        elements.append(Paragraph(desc, S["Body"]))
        elements.append(Spacer(1, 8))

    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        "<b>IMPORTANT:</b> This timeline is a general guide. Your specific deadlines and "
        "procedures depend on your state, county, and case type. Read your summons carefully. "
        "If you do not understand something, ask the court clerk or a legal aid attorney.",
        S["BodyWarning"]
    ))

    doc.build(elements)


def _generate_defenses_explained(data: dict, output_path: str):
    """Generate plain-English explanations of all eviction defenses."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    state = data.get("state", "FL").upper()
    defenses = data.get("defenses", {})

    # Master defense dictionary — plain English for every defense key used across states
    DEFENSE_GUIDE = {
        # General defenses
        "def_repairs": ("Landlord Failed to Make Repairs",
            "Also called 'breach of warranty of habitability' or 'failure to maintain.' "
            "You are saying the landlord refused to fix things like broken heat, leaking roof, "
            "mold, broken plumbing, or pests despite being notified.\n\n"
            "EVIDENCE YOU NEED: Photos/videos of the problem, dated. Written repair requests "
            "to the landlord (texts, emails, letters). Any inspection reports. Witness statements."),
        "def_failed_repair": ("Landlord Failed to Repair",
            "Same as above — the landlord knew about a problem and did not fix it. "
            "You need PROOF that you notified them (written request, dated)."),
        "def_did_repairs": ("Defendant Made Repairs",
            "You fixed the problem yourself because the landlord would not. "
            "You may be entitled to deduct the cost from rent.\n\n"
            "EVIDENCE YOU NEED: Receipts for supplies, photos of repairs, dated notice to landlord."),
        "def_amount": ("I Dispute the Amount of Rent Claimed",
            "The landlord says you owe more than you actually do. You may have already paid "
            "some of it, or the landlord overcharged you.\n\n"
            "EVIDENCE YOU NEED: Rent receipts, bank statements, canceled checks, lease agreement "
            "showing the correct rent amount. A written calculation of what you believe you owe."),
        "def_not_owed": ("I Do Not Owe the Amount Claimed",
            "Same as above — the landlord is claiming money you do not actually owe."),
        "def_paid": ("I Already Paid",
            "You paid the rent the landlord claims is owed.\n\n"
            "EVIDENCE YOU NEED: Receipts, bank statements, canceled checks, money order stubs, "
            "or payment confirmation emails/texts showing the date and amount paid."),
        "def_no_rent_due": ("No Rent Is Due",
            "You do not owe any rent — you either already paid in full, or no rent was owed."),
        "def_attempted_pay": ("I Tried to Pay But Landlord Refused",
            "You offered or tried to pay the full amount but the landlord would not accept it. "
            "This is important because it shows you acted in good faith.\n\n"
            "EVIDENCE YOU NEED: Written proof you offered to pay (texts, emails, letters). "
            "If you tried to hand them a check, a dated letter describing the attempt."),
        "def_offered_pay": ("Offered to Pay",
            "Same as above — you made a good faith offer to pay but were refused."),
        "def_retaliation": ("Retaliatory Eviction",
            "The landlord is evicting you because you exercised a legal right — like complaining "
            "to code enforcement, requesting repairs, joining a tenant union, or reporting violations.\n\n"
            "EVIDENCE YOU NEED: Dated proof of your complaint/action that triggered the retaliation. "
            "Timeline showing the eviction was filed shortly after your complaint. Any threatening "
            "communication from the landlord."),
        "def_discrimination": ("Discriminatory Eviction",
            "The eviction violates fair housing laws — you are being evicted because of your race, "
            "religion, sex, disability, family status, national origin, or other protected category.\n\n"
            "EVIDENCE YOU NEED: Any discriminatory statements by the landlord (texts, emails, witnesses). "
            "Evidence that other tenants in similar situations were treated differently."),
        "def_fair_housing": ("Fair Housing Violation",
            "Same as above — the eviction violates federal or state fair housing laws."),
        "def_bad_notice": ("Improper or No Notice",
            "The landlord did not give you proper legal notice before filing the eviction. "
            "The notice may be missing required information, or the timeline was wrong.\n\n"
            "EVIDENCE YOU NEED: The notice you received (bring it to court). State law showing "
            "what proper notice requires. Proof of WHEN you received it."),
        "def_no_notice": ("No Notice Given",
            "You never received any written notice before the eviction was filed."),
        "def_landlord_breach": ("Landlord Breached the Rental Agreement",
            "The landlord violated the lease — for example, entering without notice, shutting off "
            "utilities, removing your belongings, or failing to provide essential services.\n\n"
            "EVIDENCE YOU NEED: Your lease agreement showing the landlord's obligations. Proof of "
            "the violations (photos, dates, communications)."),
        "def_not_owner": ("The Plaintiff Is Not the Owner",
            "The person or company suing you does not actually own the property. "
            "Only the actual owner or authorized agent can file for eviction."),
        "def_waived": ("Landlord Waived the Eviction",
            "The landlord did something that canceled the eviction notice — for example, "
            "accepting rent after sending the notice, or telling you that you can stay.\n\n"
            "EVIDENCE YOU NEED: Proof the landlord accepted rent after the notice (receipt, bank "
            "statement). Written or verbal statements that the eviction is canceled. Witnesses."),
        "def_accepted_rent": ("Landlord Accepted Rent After Notice",
            "The landlord took your rent money after sending the eviction notice. This can "
            "cancel the eviction in many states."),
        "def_corrected": ("I Fixed the Problem",
            "The landlord claimed you violated the lease and you fixed it before the deadline.\n\n"
            "EVIDENCE YOU NEED: Proof of when you corrected the issue (photos, receipts, witness). "
            "Proof the correction was made before the deadline in the notice."),
        "def_admit_all": ("I Admit Everything — No Trial Needed",
            "You agree with everything the landlord claims and are not contesting the eviction. "
            "You just want to document your position and possibly negotiate move-out time."),
        "def_admit_partial": ("I Admit Partial Responsibility",
            "You agree you owe some money but not the full amount claimed by the landlord."),
        "def_deny_all": ("I Deny Everything",
            "You deny all of the landlord's claims. You believe the eviction is completely wrong."),
        "def_contest": ("I Contest Court Jurisdiction",
            "You believe this court does not have the authority to hear this case — for example, "
            "wrong county, wrong court type, or the case was filed improperly."),
        "def_other": ("Other Defenses",
            "You have another reason the eviction is wrong that is not listed on the form. "
            "Write a clear, brief explanation. Bring evidence to support it."),
    }

    elements.append(Paragraph("YOUR DEFENSES — PLAIN ENGLISH GUIDE", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        "Your Answer form lists legal defenses. This guide explains what each one means "
        "and what evidence you need to prove it. Check ONLY the defenses that are true.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))

    # Show all common defenses, highlight the ones the tenant checked
    for key, (title, explanation) in DEFENSE_GUIDE.items():
        checked = False
        if key in defenses and isinstance(defenses[key], dict):
            checked = defenses[key].get("checked", False)

        if checked:
            elements.append(Paragraph(f"<b>☑ {title} ← YOU CHECKED THIS</b>", S["BodyBold"]))
        else:
            elements.append(Paragraph(f"<b>☐ {title}</b>", S["Body"]))

        for line in explanation.split("\n"):
            if line.strip():
                elements.append(Paragraph(line.strip(), S["BodySmall"]))
        elements.append(Spacer(1, 6))

    doc.build(elements)


def _generate_evidence_guide(data: dict, output_path: str):
    """Generate an evidence gathering guide."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})

    elements.append(Paragraph("EVIDENCE GATHERING GUIDE", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<b>For:</b> {p.get('full_name', 'Tenant')}<br/>"
        "Evidence is everything in eviction court. The right evidence can win your case. "
        "This guide tells you what to gather and how to organize it.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))

    sections = [
        ("1. WRITTEN EVIDENCE — MOST IMPORTANT", [
            "Your LEASE or rental agreement — bring the entire document.",
            "All RENT RECEIPTS, bank statements, canceled checks, money order stubs.",
            "All notices from the landlord — pay or quit notice, eviction notice, ANY letter.",
            "All text messages and emails with your landlord — print them out.",
            "Any repair requests you sent — texts, emails, certified letters, work orders.",
            "Any letters from code enforcement, health department, or housing inspectors.",
            "Your eviction summons and complaint — bring ALL pages.",
        ]),
        ("2. PHOTOS & VIDEO", [
            "Take photos of EVERY repair issue — broken appliances, leaks, mold, pests, damage.",
            "Date each photo. Use a newspaper in the photo to prove the date if needed.",
            "Take photos of the ENTIRE unit — show overall condition.",
            "If safe, take photos of the outside — building condition, trash, hazards.",
            "Video walkthrough: Narrate as you film. 'Today is [date]. This is the leaking ceiling...'",
        ]),
        ("3. WITNESSES", [
            "Neighbors who saw or heard problems — ask them to come to court or write a statement.",
            "Other tenants in your building facing similar issues — compare notes.",
            "Anyone who was present when your landlord said or did something relevant.",
            "Witness statement format: name, address, phone, date, what they saw/heard, signature.",
        ]),
        ("4. ORGANIZATION — CRITICAL", [
            "Put everything in chronological order — oldest first.",
            "Create a simple TIMELINE: Date → What happened → Evidence you have.",
            "Use a 3-ring binder or folder with tabs for each category.",
            "Make 3 copies of EVERYTHING — one for the judge, one for the landlord, one for you.",
            "Write a brief SUMMARY (1 page max) of your case — key dates and facts.",
        ]),
    ]

    for title, items in sections:
        elements.append(Paragraph(f"<b>{title}</b>", S["BodyBold"]))
        for item in items:
            elements.append(Paragraph(f"• {item}", S["Body"]))
        elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        "<b>DO NOT</b> bring original documents to court unless you have copies. "
        "The court keeps what you file — do NOT give away your only copy of anything.",
        S["BodyWarning"]
    ))

    doc.build(elements)


def _generate_income_expense_worksheet(data: dict, output_path: str):
    """Generate an income and expense worksheet for fee waivers and rental assistance."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})

    elements.append(Paragraph("INCOME & EXPENSE WORKSHEET", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<b>For:</b> {p.get('full_name', 'Tenant')}<br/>"
        "Use this worksheet to list your monthly income and expenses. "
        "You will need this information for fee waivers, rental assistance applications, "
        "and to show the judge your financial situation.",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))

    # Income section
    elements.append(Paragraph("<b>MONTHLY INCOME</b>", S["BodyBold"]))
    income_items = [
        "Wages / salary (after taxes):  $___________",
        "Self-employment income:         $___________",
        "Social Security / SSI / SSDI:   $___________",
        "Unemployment benefits:           $___________",
        "Child support / alimony:         $___________",
        "SNAP (food stamps):              $___________",
        "TANF / cash assistance:          $___________",
        "Other income:                    $___________",
        "",
        "<b>TOTAL MONTHLY INCOME:          $___________</b>",
    ]
    for item in income_items:
        if item:
            elements.append(Paragraph(item, S["Body"]))
        else:
            elements.append(Spacer(1, 3))

    elements.append(Spacer(1, 16))

    # Expenses section
    elements.append(Paragraph("<b>MONTHLY EXPENSES</b>", S["BodyBold"]))
    expense_items = [
        "Rent / mortgage:                 $___________",
        "Utilities (electric, gas, water):$___________",
        "Phone / internet:                 $___________",
        "Food / groceries:                 $___________",
        "Transportation (gas, bus, car):   $___________",
        "Car payment:                      $___________",
        "Car insurance:                    $___________",
        "Health insurance / medical:       $___________",
        "Child care:                       $___________",
        "Credit card / loan payments:      $___________",
        "Other expenses:                   $___________",
        "",
        "<b>TOTAL MONTHLY EXPENSES:         $___________</b>",
    ]
    for item in expense_items:
        if item:
            elements.append(Paragraph(item, S["Body"]))
        else:
            elements.append(Spacer(1, 3))

    elements.append(Spacer(1, 16))

    elements.append(Paragraph("<b>ASSETS</b>", S["BodyBold"]))
    elements.append(Paragraph("Cash on hand:                     $___________", S["Body"]))
    elements.append(Paragraph("Bank account(s) balance:          $___________", S["Body"]))
    elements.append(Paragraph("Vehicle (make/model/year):        _______________", S["Body"]))
    elements.append(Paragraph("Other assets:                     _______________", S["Body"]))
    elements.append(Spacer(1, 12))

    elements.append(Paragraph("<b>HOUSEHOLD INFORMATION</b>", S["BodyBold"]))
    elements.append(Paragraph("Number of adults in home:         _______________", S["Body"]))
    elements.append(Paragraph("Number of children in home:       _______________", S["Body"]))
    elements.append(Paragraph("Dependents claimed on taxes:      _______________", S["Body"]))

    elements.append(Spacer(1, 16))
    elements.append(Paragraph(
        "<b>TIP:</b> Most fee waivers and rental assistance programs use this same "
        "information. Fill out this worksheet ONCE and use it for all applications.",
        S["BodySmall"]
    ))

    doc.build(elements)


def _generate_demand_letter(data: dict, output_path: str):
    """Generate a formal demand letter to the landlord for repairs/remedies."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=1*inch, bottomMargin=1*inch,
                            leftMargin=1*inch, rightMargin=1*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    today = date.today().strftime("%B %d, %Y")

    elements.append(Paragraph(today, S["Body"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph("VIA CERTIFIED MAIL — RETURN RECEIPT REQUESTED", S["BodyBold"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(l.get("landlord_name", "Landlord"), S["Body"]))
    elements.append(Paragraph(l.get("landlord_address", ""), S["Body"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"<b>RE:</b> DEMAND FOR REPAIRS — {p.get('property_address', '')}<br/>"
        f"&nbsp;&nbsp;&nbsp;&nbsp;Case No: {c.get('case_number', 'N/A')}",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(f"Dear {l.get('landlord_name', 'Landlord')},", S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "I am writing to formally demand that you make necessary repairs to the "
        "rental property identified above. As you know, the following conditions "
        "exist at the property and violate the warranty of habitability:",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "________________________________________________________________________________",
        S["Body"]
    ))
    elements.append(Paragraph(
        "________________________________________________________________________________",
        S["Body"]
    ))
    elements.append(Paragraph(
        "________________________________________________________________________________",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "These conditions affect the health and safety of my household. I have previously "
        "notified you of these issues on multiple occasions. This letter serves as formal "
        "written notice pursuant to state law.",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        f"I request that you complete all repairs within 7 days of receiving this letter. "
        f"If the repairs are not completed, I will pursue all legal remedies available, "
        f"including filing a complaint with code enforcement and using this letter as "
        f"evidence in eviction court.",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "You may contact me at the phone number or email below to arrange access for repairs.",
        S["Body"]
    ))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph("Sincerely,", S["Body"]))
    elements.append(Spacer(1, 18))
    elements.append(Paragraph(p.get("full_name", ""), S["Body"]))
    elements.append(Paragraph(p.get("phone", ""), S["BodySmall"]))
    elements.append(Paragraph(p.get("email", ""), S["BodySmall"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "<b>INSTRUCTIONS:</b> Mail this letter by CERTIFIED MAIL with RETURN RECEIPT. "
        "Keep the receipt and a copy of this letter. The postmark and receipt prove you "
        "gave written notice — this is critical evidence in court.",
        S["BodySmall"]
    ))

    doc.build(elements)


def _generate_cover_page(data: dict, paths: dict, output_path: str):
    """Generate a cover page with document index for the packet."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=1*inch, bottomMargin=1*inch,
                            leftMargin=1*inch, rightMargin=1*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    c = data.get("case_details", {})
    l = data.get("landlord_info", {})
    state = data.get("state", "").upper()

    today = date.today().strftime("%B %d, %Y")

    elements.append(Spacer(1, 1.5*inch))
    elements.append(Paragraph("EVICTION DEFENSE PACKET", S["FormTitle"]))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(
        f"<b>Prepared for:</b> {p.get('full_name', 'Tenant')}<br/>"
        f"<b>Date:</b> {today}",
        S["Body"]
    ))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        f"<b>Case:</b> {l.get('landlord_name', 'Landlord')} v. {p.get('full_name', 'Tenant')}<br/>"
        f"<b>Case No:</b> {c.get('case_number', 'N/A')}<br/>"
        f"<b>County:</b> {p.get('county', 'N/A')}, {state}",
        S["BodySmall"]
    ))
    elements.append(Spacer(1, 0.5*inch))
    elements.append(HRFlowable(width="100%", thickness=1))
    elements.append(Spacer(1, 12))

    # Document index
    elements.append(Paragraph("<b>DOCUMENTS IN THIS PACKET</b>", S["BodyBold"]))
    elements.append(Spacer(1, 8))

    DOC_DESCRIPTIONS = {
        "emergency_action_plan": ("Emergency Action Plan", "What to do today — step-by-step 24-hour action plan"),
        "eviction_timeline": ("Eviction Process Timeline", "Understand the entire eviction process from notice to judgment"),
        "defenses_explained": ("Your Defenses Explained", "Plain-English guide to every legal defense on your Answer form"),
        "evidence_guide": ("Evidence Gathering Guide", "What to collect and how to organize it for court"),
        "income_expense_worksheet": ("Income & Expense Worksheet", "For fee waivers and rental assistance applications"),
        "filing_checklist": ("Filing Checklist", "Step-by-step instructions to file your Answer with the court"),
        "court_checklist": ("Court Hearing Checklist", "What to bring and what to expect at your hearing"),
        "hearing_script": ("Hearing Script", "What to say to the judge — personalized for your case"),
        "fee_waiver": ("Fee Waiver Instructions", "How to file your case for free if you can't afford the fee"),
        "rental_assistance": ("Rental Assistance Resources", "Local organizations that can help with rent and housing"),
        "demand_letter": ("Demand Letter to Landlord", "Formal written demand for repairs — critical for building your case"),
        "payment_plan_letter": ("Payment Plan Letter", "Formal request to your landlord to set up a payment plan"),
        "hardship_letter": ("Hardship Letter", "Request for more time due to financial hardship"),
        "motion_to_determine_rent": ("Motion to Determine Rent", "Court motion to dispute the amount of rent claimed"),
    }

    ALWAYS_DOCS = ["emergency_action_plan", "eviction_timeline", "defenses_explained",
                   "evidence_guide", "income_expense_worksheet", "filing_checklist",
                   "court_checklist", "hearing_script", "fee_waiver",
                   "rental_assistance"]
    COND_DOCS = ["demand_letter", "motion_to_determine_rent", "payment_plan_letter", "hardship_letter"]

    doc_num = 1
    for key in ALWAYS_DOCS:
        if key in paths:
            desc = DOC_DESCRIPTIONS.get(key, (key, ""))
            elements.append(Paragraph(
                f"<b>Document {doc_num}:</b> {desc[0]} — {desc[1]}",
                S["Body"]
            ))
            doc_num += 1

    # Conditional docs
    has_conditional = any(k in paths for k in COND_DOCS)
    if has_conditional:
        elements.append(Spacer(1, 8))
        elements.append(Paragraph("<b>ADDITIONAL DOCUMENTS:</b>", S["BodyBold"]))
        for key in COND_DOCS:
            if key in paths:
                desc = DOC_DESCRIPTIONS.get(key, (key, ""))
                elements.append(Paragraph(
                    f"<b>Document {doc_num}:</b> {desc[0]} — {desc[1]}",
                    S["Body"]
                ))
                doc_num += 1

    elements.append(Spacer(1, 0.5*inch))
    elements.append(HRFlowable(width="100%", thickness=1))
    elements.append(Spacer(1, 12))

    # Urgent instructions
    elements.append(Paragraph("<b>URGENT — READ THIS FIRST</b>", S["BodyBold"]))
    elements.append(Spacer(1, 6))
    for line in [
        "1. Your eviction summons has a DEADLINE. Find it on your court papers NOW. Mark it on your calendar.",
        "2. Sign and file your Answer form (separate PDF) BEFORE the deadline.",
        "3. If you can't afford the filing fee, submit the fee waiver form (also a separate PDF) at the same time.",
        "4. Keep a stamped copy of everything you file with the court.",
        "5. Bring this entire packet to your court hearing.",
    ]:
        elements.append(Paragraph(line, S["Body"]))
        elements.append(Spacer(1, 3))

    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "<i>This packet was generated by an automated document preparation service. "
        "It does not constitute legal advice. If you need legal advice, contact a "
        "licensed attorney in your state.</i>",
        S["BodySmall"]
    ))

    doc.build(elements)


# ======================== STYLES ========================

def _get_styles():
    """Get shared ReportLab styles for document generation."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        "Caption", parent=styles["Normal"],
        fontSize=9, leading=12, alignment=TA_CENTER,
        spaceAfter=6,
    ))
    styles.add(ParagraphStyle(
        "FormTitle", parent=styles["Normal"],
        fontSize=13, leading=16, alignment=TA_CENTER,
        spaceAfter=6, spaceBefore=6,
    ))
    styles.add(ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=14, alignment=TA_LEFT,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "BodyBold", parent=styles["Normal"],
        fontSize=10, leading=14, alignment=TA_LEFT,
        spaceAfter=4,
    ))
    styles.add(ParagraphStyle(
        "BodySmall", parent=styles["Normal"],
        fontSize=9, leading=12, alignment=TA_LEFT,
        spaceAfter=3,
    ))
    styles.add(ParagraphStyle(
        "BodyWarning", parent=styles["Body"],
        textColor=colors.red, fontSize=10, leading=14,
    ))

    return styles
