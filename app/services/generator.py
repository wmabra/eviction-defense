"""
PDF Document Generator — produces the complete self-help paperwork packet.

Generates all 8 documents in the $395 packet from confirmed customer data:
1. Form 1.947(b) Answer — Residential Eviction (ReportLab PDF)
2. Motion to Determine Rent (ReportLab PDF)
3. Landlord Payment-Plan Letter (python-docx)
4. Hardship/Extension Letter (python-docx)
5. Filing Checklist (plain PDF)
6. Court Checklist (plain PDF)
7. Hearing Script — What to Say in Court (plain PDF)
8. Fee Waiver Instructions (plain PDF)
9. E-Filing Instructions (python-docx)
10. Rental Assistance Resource Sheet (python-docx)
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

    # 2. Motion to Determine Rent (conditional)
    defenses = base.get("defenses", {})
    if defenses.get("def_amount", {}).get("checked"):
        mtr_path = os.path.join(output_dir, "02_motion_to_determine_rent.pdf")
        _generate_motion_to_determine_rent(base, mtr_path)
        paths["motion_to_determine_rent"] = mtr_path

    # 3. Landlord Payment-Plan Letter
    if base.get("preferences", {}).get("wants_payment_plan"):
        pplan_path = os.path.join(output_dir, "03_payment_plan_letter.docx")
        _generate_payment_plan_letter(base, pplan_path)
        paths["payment_plan_letter"] = pplan_path

    # 4. Hardship Letter
    if base.get("preferences", {}).get("needs_more_time"):
        hardship_path = os.path.join(output_dir, "04_hardship_letter.docx")
        _generate_hardship_letter(base, hardship_path)
        paths["hardship_letter"] = hardship_path

    # 5. Filing Checklist
    checklist_path = os.path.join(output_dir, "05_filing_checklist.pdf")
    _generate_filing_checklist(base, checklist_path)
    paths["filing_checklist"] = checklist_path

    # 6. Court Checklist
    court_checklist_path = os.path.join(output_dir, "06_court_checklist.pdf")
    _generate_court_checklist(base, court_checklist_path)
    paths["court_checklist"] = court_checklist_path

    # 7. Hearing Script
    hearing_path = os.path.join(output_dir, "07_hearing_script.pdf")
    _generate_hearing_script(base, hearing_path)
    paths["hearing_script"] = hearing_path

    # 8. Fee Waiver Instructions
    fee_waiver_path = os.path.join(output_dir, "08_fee_waiver.pdf")
    _generate_fee_waiver(base, fee_waiver_path)
    paths["fee_waiver"] = fee_waiver_path

    # 9. E-Filing Instructions
    efiling_path = os.path.join(output_dir, "07_e_filing_instructions.docx")
    _generate_efiling_instructions(base, efiling_path)
    paths["e_filing_instructions"] = efiling_path

    # 8. Rental Assistance Sheet
    rental_path = os.path.join(output_dir, "08_rental_assistance_resources.docx")
    _generate_rental_assistance_sheet(base, rental_path)
    paths["rental_assistance"] = rental_path

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
    """Generate landlord payment-plan request letter."""
    from docx import Document
    from docx.shared import Pt, Inches
    from docx.enum.text import WD_ALIGN_PARAGRAPH

    doc = Document()
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    pref = data.get("preferences", {})

    # Date
    doc.add_paragraph(date.today().strftime("%B %d, %Y"))

    # Landlord address
    doc.add_paragraph("")
    doc.add_paragraph(l.get("landlord_name", ""))
    doc.add_paragraph(l.get("landlord_address", ""))
    doc.add_paragraph("")

    # Re:
    doc.add_paragraph(f"RE: Payment Plan Request — Property at {p.get('property_address', '')}")
    doc.add_paragraph(f"    Case No: {c.get('case_number', '')}")
    doc.add_paragraph("")

    # Body
    doc.add_paragraph(f"Dear {l.get('landlord_name', 'Landlord')},")
    doc.add_paragraph("")
    body = doc.add_paragraph()
    body.add_run(
        f"I am writing to request a payment plan to address the outstanding rent balance "
        f"of ${c.get('complaint_amount_claimed', '0')}. I am committed to fulfilling my "
        f"obligations under the lease and propose the following payment arrangement:"
    )

    doc.add_paragraph("")
    doc.add_paragraph(f"Monthly payment: ${pref.get('payment_plan_amount', '_____')}")
    doc.add_paragraph("Payment due on: The _____ day of each month")
    doc.add_paragraph("Start date: _________________")
    doc.add_paragraph("")

    doc.add_paragraph(
        "I am requesting this arrangement due to temporary financial hardship. "
        "I will make every effort to adhere to this schedule."
    )
    doc.add_paragraph("")
    doc.add_paragraph("Thank you for your consideration.")
    doc.add_paragraph("")
    doc.add_paragraph("Sincerely,")
    doc.add_paragraph("")
    doc.add_paragraph(p.get("full_name", ""))
    doc.add_paragraph(p.get("phone", ""))
    doc.add_paragraph(p.get("email", ""))

    doc.save(output_path)


def _generate_hardship_letter(data: dict, output_path: str):
    """Generate hardship/extension letter."""
    from docx import Document
    doc = Document()
    p = data.get("personal_info", {})
    l = data.get("landlord_info", {})
    c = data.get("case_details", {})
    pref = data.get("preferences", {})

    doc.add_paragraph(date.today().strftime("%B %d, %Y"))
    doc.add_paragraph("")
    doc.add_paragraph(l.get("landlord_name", ""))
    doc.add_paragraph(l.get("landlord_address", ""))
    doc.add_paragraph("")
    doc.add_paragraph(f"RE: Hardship Request — {p.get('property_address', '')}")
    doc.add_paragraph(f"    Case No: {c.get('case_number', '')}")
    doc.add_paragraph("")

    doc.add_paragraph(f"Dear {l.get('landlord_name', 'Landlord')},")
    doc.add_paragraph("")
    doc.add_paragraph(
        "I am writing to respectfully request additional time to vacate the premises "
        "due to the following circumstances:"
    )
    doc.add_paragraph("")
    doc.add_paragraph(pref.get("hardship_reason", "________________________________________________________________________"))
    doc.add_paragraph("")
    doc.add_paragraph(
        "I understand my obligations under the lease and I am not seeking to avoid them. "
        "I am simply requesting a short extension to allow me to make arrangements."
    )
    doc.add_paragraph("")
    doc.add_paragraph("I am requesting an extension until: _________________")
    doc.add_paragraph("")
    doc.add_paragraph("Thank you for your understanding.")
    doc.add_paragraph("")
    doc.add_paragraph("Sincerely,")
    doc.add_paragraph("")
    doc.add_paragraph(p.get("full_name", ""))
    doc.add_paragraph(p.get("phone", ""))
    doc.add_paragraph(p.get("email", ""))

    doc.save(output_path)


# ======================== CHECKLISTS ========================

def _generate_filing_checklist(data: dict, output_path: str):
    """Generate a step-by-step filing checklist PDF."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    styles = _get_styles()
    elements = []
    S = styles

    elements.append(Paragraph("FILING CHECKLIST", S["FormTitle"]))
    elements.append(Spacer(1, 12))
    elements.append(Paragraph(
        "Follow these steps to file your Answer with the court. "
        "Check off each item as you complete it.", S["Body"]
    ))
    elements.append(Spacer(1, 12))

    steps = [
        ("☐ Step 1: Review Your Packet",
         "Read through all documents. Make sure everything looks correct."),
        ("☐ Step 2: Sign the Answer Form",
         "Sign and date the Form 1.947(b) Answer where indicated."),
        ("☐ Step 3: Make Copies",
         "Make at least 3 copies of EVERY document in your packet."),
        ("☐ Step 4: File with the Court Clerk",
         f"Take the original + 2 copies to the county courthouse where "
         f"your case was filed. Ask the clerk to stamp all copies as 'Filed'."),
        ("☐ Step 5: Pay Filing Fee (or Request Waiver)",
         "There may be a filing fee. If you cannot afford it, ask the clerk "
         "for an 'Affidavit of Indigency' form."),
        ("☐ Step 6: Serve the Landlord",
         "You must deliver a copy of your filed Answer to the landlord or "
         "their attorney. Keep proof of delivery (certified mail receipt, "
         "hand-delivery receipt, or email confirmation)."),
        ("☐ Step 7: Deposit Rent into Court Registry",
         "If you raised any defense other than 'I already paid,' you must "
         "deposit the rent into the court registry. Check with the clerk "
         "for the exact amount and process."),
        ("☐ Step 8: Note Your Deadline",
         f"Your response deadline is shown on your summons. Count 5 business "
         f"days (excluding weekends and holidays) from the date you were served."),
        ("☐ Step 9: Prepare for Hearing",
         "If a hearing is scheduled, bring all your documents, evidence, "
         "and a list of what you want to say to the judge."),
        ("☐ Step 10: Attend All Court Dates",
         "If you miss a court date, the judge may enter a default judgment "
         "against you."),
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
    """Generate a sample script for what to say in court."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    
    elements.append(Paragraph("YOUR COURT HEARING SCRIPT", S["FormTitle"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "This script helps you speak to the judge. You can bring this paper with you.",
        S["Body"]
    ))
    elements.append(Spacer(1, 14))
    
    script_lines = [
        ("<b>WHEN YOUR CASE IS CALLED:</b> Walk to the front.", False),
        (f"<b>You:</b> Good morning/afternoon, Your Honor. My name is {p.get('full_name', '[YOUR NAME]')}.", True),
        ("<b>Judge:</b> Do you have an attorney?", False),
        ("<b>You:</b> No, Your Honor. I am representing myself.", True),
        ("<b>Judge:</b> Have you filed your Answer?", False),
        ("<b>You:</b> Yes, Your Honor. Here is a copy. (hand judge copy)", True),
        ("<b>Judge:</b> Do you owe the rent?", False),
        ("<b>You:</b> I dispute the amount claimed OR Yes, and I deposited it with the court.", True),
        ("<b>EXPLAIN YOUR DEFENSE:</b> Tell the judge briefly why you should not be evicted.", False),
        ("Examples: Landlord refused repairs / Retaliation / Improper notice / Already paid", False),
        ("<b>IF YOU NEED MORE TIME:</b>", False),
        ("<b>You:</b> Your Honor, I request more time to find housing or make arrangements.", True),
        ("<b>CLOSING:</b> Thank you for hearing me, Your Honor.", True),
    ]
    
    for text, _ in script_lines:
        elements.append(Paragraph(text, S["Body"]))
        elements.append(Spacer(1, 6))
    
    elements.append(Spacer(1, 14))
    elements.append(Paragraph("<b>TIPS:</b> Dress neatly. No phone. Do not interrupt. Bring all documents.", S["BodySmall"]))
    
    doc.build(elements)


# ======================== FEE WAIVER ========================

def _generate_fee_waiver(data: dict, output_path: str):
    """Generate fee waiver instructions — state-specific."""
    doc = SimpleDocTemplate(output_path, pagesize=letter,
                            topMargin=0.75*inch, bottomMargin=0.75*inch)
    S = _get_styles()
    elements = []
    p = data.get("personal_info", {})
    county = p.get('county', 'your county')
    
    # State-specific fee waiver info
    waiver_info = {
        "FL": {"form": "Form 12.902(e)", "site": "www.flcourts.gov", "fee": "$295"},
        "CA": {"form": "Form FW-001", "site": "www.courts.ca.gov", "fee": "$240-$450"},
        "TX": {"form": "Statement of Inability to Afford Payment of Court Costs", "site": "www.txcourts.gov", "fee": "varies by court"},
        "IL": {"form": "Application for Waiver of Court Fees", "site": "www.illinoiscourts.gov", "fee": "varies by county"},
        "MI": {"form": "MC 20 Fee Waiver Request", "site": "www.courts.michigan.gov", "fee": "varies by court"},
        "NV": {"form": "Application to Proceed In Forma Pauperis", "site": "www.civillawselfhelpcenter.org", "fee": "varies by court"},
        "OR": {"form": "Application for Deferral or Waiver of Fees", "site": "www.courts.oregon.gov", "fee": "varies by court"},
        "MN": {"form": "In Forma Pauperis Affidavit", "site": "www.mncourts.gov", "fee": "varies by court"},
    }
    info = waiver_info.get(data.get("state", "FL").upper(), waiver_info.get("FL", {"form": "fee waiver form", "site": "your state court website", "fee": "varies"}))
    
    elements.append(Paragraph("FEE WAIVER — FILE YOUR CASE FOR FREE", S["FormTitle"]))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(f"<b>For:</b> {county}", S["Body"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(
        "If you cannot afford the court filing fee, you can ask the court to waive it. "
        "This is called filing \"In Forma Pauperis\" or an Affidavit of Indigency.",
        S["Body"]
    ))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>YOUR STATE USES: {info['form']}</b>", S["BodyBold"]))
    elements.append(Paragraph(f"Download from: {info['site']}", S["BodySmall"]))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>HOW TO FILE:</b>", S["BodyBold"]))
    for step in [
        f"1. Download {info['form']} from {info['site']} OR ask the court clerk for a copy",
        "2. Fill out your income, expenses, assets, and number of dependents",
        "3. Sign the form in front of the court clerk (they notarize for free) or any notary",
        f"4. Submit the fee waiver ALONG with your Answer before the deadline",
        f"5. Judge reviews your financial situation — if approved, you pay $0 instead of {info['fee']}",
    ]:
        elements.append(Paragraph(step, S["Body"]))
        elements.append(Spacer(1, 3))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>WHO QUALIFIES:</b> You receive public benefits (SNAP, Medicaid, SSI) OR your income is below 200% of federal poverty level OR paying the fee would cause hardship.", S["BodySmall"]))
    elements.append(Paragraph("<b>IMPORTANT:</b> File the fee waiver AND your Answer together BEFORE the deadline. Even if the waiver is denied, you must still file on time.", S["BodyWarning"]))
    
    doc.build(elements)


# ======================== E-FILING INSTRUCTIONS ========================

def _generate_efiling_instructions(data: dict, output_path: str):
    """Generate Florida e-filing portal instructions."""
    from docx import Document
    doc = Document()

    doc.add_heading("E-Filing Instructions — Florida Courts E-Filing Portal", level=1)
    doc.add_paragraph("")

    sections = [
        ("Step 1: Create an Account",
         "Go to https://www.myflcourtaccess.com\n"
         "Click 'Register' and select 'Self-Represented Litigant'\n"
         "Fill in your name, email, and create a password\n"
         "You will receive a confirmation email — click the link to activate."),
        ("Step 2: Log In",
         "Go to myflcourtaccess.com and log in with your email and password."),
        ("Step 3: File a Document",
         "Click 'File a New Case' or 'File to an Existing Case'\n"
         "Enter your case number: " + data.get("case_details", {}).get("case_number", "") + "\n"
         "Select the county where your case was filed.\n"
         "Upload your signed Answer form (PDF or DOCX).\n"
         "Select the document type as 'Answer to Complaint.'"),
        ("Step 4: Pay Filing Fee",
         "If a fee is required, you'll be prompted to pay by credit/debit card.\n"
         "A convenience fee (3.5%) applies to card payments.\n"
         "If you cannot afford the fee, file an 'Affidavit of Indigency' instead."),
        ("Step 5: Service",
         "The portal will send a copy to the landlord/attorney if they have an account.\n"
         "You may also need to mail or hand-deliver a copy separately.\n"
         "Complete the Certificate of Service at the bottom of your Answer form."),
        ("Step 6: Keep Your Confirmation",
         "After filing, you'll receive a confirmation email with a filing ID.\n"
         "Save this email and the stamped copies of your documents."),
    ]

    for title, body in sections:
        doc.add_heading(title, level=2)
        for line in body.split("\n"):
            doc.add_paragraph(line, style="List Bullet")
        doc.add_paragraph("")

    doc.add_paragraph("")
    doc.add_paragraph("Need help? Call the Florida Courts E-Filing Authority at (850) 385-4509")
    doc.save(output_path)


# ======================== RENTAL ASSISTANCE ========================

def _generate_rental_assistance_sheet(data: dict, output_path: str):
    """Generate county-specific rental assistance resources from state databases."""
    from docx import Document
    import os
    
    doc = Document()
    state = data.get("state", "FL").upper()
    county = data.get("personal_info", {}).get("county", "your county")
    full_name = data.get("personal_info", {}).get("full_name", "Tenant")

    # Load state database if available
    db_dir = os.path.join(os.path.dirname(__file__), "..", "..", "databases")
    resources = []
    
    # Map state codes to database filenames
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
                # Find the data sheet (may be 'Verified Resources' or the first sheet)
                ws = wb['Verified Resources'] if 'Verified Resources' in wb.sheetnames else wb.active
                # Auto-detect header row (look for 'Organization' in the first 5 rows)
                header_row = 1
                for r in range(1, min(6, ws.max_row + 1)):
                    for c in range(1, ws.max_column + 1):
                        val = str(ws.cell(r, c).value or '').strip()
                        if val == 'Organization':
                            header_row = r
                            break
                    if header_row > 1:
                        break
                # Build column index
                col_map = {}
                for c in range(1, ws.max_column + 1):
                    hdr = str(ws.cell(header_row, c).value or '').strip()
                    if 'county' in hdr.lower():
                        col_map['county'] = c
                    elif 'category' in hdr.lower():
                        col_map['category'] = c
                    elif 'organization' in hdr.lower():
                        col_map['organization'] = c
                    elif 'program' in hdr.lower() or 'service' in hdr.lower():
                        col_map['program'] = c
                    elif 'website' in hdr.lower():
                        col_map['website'] = c
                    elif 'phone' in hdr.lower():
                        col_map['phone'] = c
                    elif 'eligibility' in hdr.lower():
                        col_map['eligibility'] = c
                for row in range(header_row + 1, ws.max_row + 1):
                    r_county = str(ws.cell(row, col_map.get('county', 1)).value or "").strip()
                    if r_county.lower() == county.lower():
                        resources.append({
                            "category": str(ws.cell(row, col_map.get('category', 2)).value or ""),
                            "organization": str(ws.cell(row, col_map.get('organization', 3)).value or ""),
                            "program": str(ws.cell(row, col_map.get('program', 4)).value or ""),
                            "website": str(ws.cell(row, col_map.get('website', 5)).value or ""),
                            "phone": str(ws.cell(row, col_map.get('phone', 6)).value or ""),
                            "eligibility": str(ws.cell(row, col_map.get('eligibility', 8)).value or ""),
                        })
                wb.close()
            except Exception as e:
                logger.warning(f"Could not load resource database: {e}")

    # Phone number lookup — loads verified numbers from state resource JSON files.
    # Falls back to national numbers. The customer pays $395; they should not
    # have to research phone numbers themselves.
    import json
    resource_json = os.path.join(os.path.dirname(__file__), f"{state.lower()}_resources.json")
    known_phones = {
        "HUD": "1-800-569-4287",
        "United Way": "2-1-1",
        "211": "2-1-1",
        "Eviction Legal Helpline": "1-833-NOEVICT",
    }
    if os.path.exists(resource_json):
        try:
            with open(resource_json) as f:
                state_data = json.load(f)
            # Merge statewide numbers
            if "statewide" in state_data:
                known_phones.update(state_data["statewide"])
            # Get county-specific numbers by region
            counties = state_data.get("counties", {})
            regions = state_data.get("regions", {})
            county_info = counties.get(county, {})
            region = county_info.get("_region", "")
            if region and region in regions:
                known_phones.update(regions[region])
        except Exception as e:
            logger.warning(f"Could not load resource JSON: {e}")

    # Substitute placeholder phone numbers with known real numbers
    placeholder_phones = {"Research / verify", "Research/verify", "N/A", "None", "See website", "Find local office", ""}
    for r in resources:
        phone = r.get("phone", "").strip()
        org = r.get("organization", "").strip()
        cat = r.get("category", "").strip()
        if phone in placeholder_phones:
            found = None
            # Try keyword matching against category and organization
            search_text = (cat + " " + org).lower()
            for keyword, num in known_phones.items():
                if keyword.lower() in search_text:
                    found = num
                    break
            # Fallback: map edge-case categories to closest match
            if not found:
                fallback_map = {
                    "SHIP": "Housing Department",
                    "Section 8": "Housing Authority",
                    "Voucher": "Housing Authority",
                    "Public Housing": "Housing Authority",
                }
                for fkw, target in fallback_map.items():
                    if fkw.lower() in search_text and target in known_phones:
                        found = known_phones[target]
                        break
            if found:
                r["phone"] = found

    # Document header
    doc.add_heading("Rental Assistance & Eviction Support Resources", level=1)
    doc.add_paragraph(f"Prepared for: {full_name}")
    doc.add_paragraph(f"County: {county}, {state}")
    doc.add_paragraph("")

    if resources:
        # Group by category
        from collections import defaultdict
        by_category = defaultdict(list)
        for r in resources:
            by_category[r["category"]].append(r)

        doc.add_heading(f"Resources in {county} County", level=2)
        doc.add_paragraph(f"Found {len(resources)} verified resources. Contact these organizations as soon as possible — funds are limited.")
        doc.add_paragraph("")

        for category, items in by_category.items():
            doc.add_heading(category, level=3)
            for item in items:
                org = item["organization"]
                prog = item["program"]
                phone = item["phone"]
                web = item["website"]
                elig = item["eligibility"]
                
                # Build bullet text
                bullet = f"{org}"
                if prog and prog != "None":
                    bullet += f" — {prog}"
                doc.add_paragraph(bullet, style="List Bullet")
                
                if phone and phone not in ("None", "N/A", "See website", "Find local office", "Research / verify", "Research/verify", ""):
                    doc.add_paragraph(f"Phone: {phone}")
                elif web and web not in ("None", "N/A"):
                    doc.add_paragraph(f"Phone: Call 211 or visit website for current contact info")
                if web and web not in ("None", "N/A"):
                    doc.add_paragraph(f"Website: {web}")
                if elig and elig not in ("None", "N/A"):
                    p = doc.add_paragraph()
                    p.add_run(f"Note: {elig[:200]}").italic = True
                doc.add_paragraph("")
    else:
        # No database available — provide general guidance
        doc.add_heading("How to Find Help", level=2)
        doc.add_paragraph("Dial 211 from any phone — United Way's free referral service for rent, utility, food, and emergency assistance.")
        doc.add_paragraph("")
        doc.add_paragraph("Visit your county's official website and search for 'rental assistance' or 'housing programs.'")
        doc.add_paragraph("")
        doc.add_paragraph("Contact your local Legal Aid office — search online for '[your county] legal aid'.")

    # Statewide resources (always included)
    doc.add_paragraph("")
    doc.add_heading("Statewide Resources", level=2)
    doc.add_paragraph("United Way 2-1-1 — Dial 211 for local assistance referrals", style="List Bullet")
    doc.add_paragraph("HUD-approved housing counselors: 1-800-569-4287 or hud.gov/counseling", style="List Bullet")
    doc.add_paragraph("Legal Services Corporation — Find your local legal aid: lsc.gov", style="List Bullet")

    # Tips
    doc.add_paragraph("")
    doc.add_heading("Tips for Applying", level=2)
    tips = [
        "Apply as soon as possible — funds are limited and programs close when money runs out.",
        "Have these documents ready: lease, eviction notice/court papers, ID, proof of income.",
        "Many programs can pay back rent directly to your landlord — ask about this option.",
        "If you have a pending application, tell the judge at your eviction hearing.",
        "Some programs require landlord cooperation — contact your landlord early.",
        "Keep copies of all applications, emails, and reference numbers.",
    ]
    for tip in tips:
        doc.add_paragraph(tip, style="List Bullet")

    doc.save(output_path)


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
