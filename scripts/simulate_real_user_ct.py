"""
Two-agent real-user simulation for Connecticut eviction defense intake:
Agent 1: AI Intake Specialist (system prompt from app.services.chat)
Agent 2: Sarah Jenkins (tenant persona in New Haven, CT)

Runs the conversation end-to-end, extracts collected data, builds all 21 PDF documents,
and audits both the chat trajectory and generated court forms for errors.
"""
import os
import sys
import re
import json
import fitz
import copy
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.chat import get_chat_response, _get_client
from app.services.generator import generate_packet
from app.services.pdf_overlay import fill_answer_form, fill_fee_waiver

TENANT_PERSONA = """You are Sarah Jenkins, a real tenant facing eviction in New Haven, Connecticut.
Your factual profile:
- Legal name: Sarah Jenkins
- Date of birth: 04/12/1988
- County: New Haven
- Street address being evicted from: 142 Willow Street, Apt 2B (do not give city/zip unless asked)
- City: New Haven
- ZIP code: 06511
- Cell phone: (203) 555-0192
- Email: sarah.jenkins@example.com
- Are you tenant named: Yes
- Foreign language interpreter needed: No
- Landlord or company name: Elm City Residential Properties, LLC
- Landlord mailing address: 500 Church Street, New Haven, CT 06510
- Landlord phone: None
- Landlord email: None
- Attorney listed for landlord: Yes
- Attorney name: David Vance, Esq.
- Attorney address: 265 Orange Street, New Haven, CT 06510
- Case/docket number: NNH-CV24-6019876
- Courthouse: New Haven Housing Session, 121 Elm Street, New Haven, CT 06510
- Division: None
- Summons service date: 05/18/2024
- Notice to quit received: Yes
- Rent claimed in complaint: $2,700.00
- Court date scheduled: Yes, on 06/05/2024 at 9:30 AM
- Response deadline: 5 days
- Monthly rent: $1,350.00
- Agree with amount: No, actually owe $1,100.00
- Why disagree: Heating boiler was broken for 8 weeks and landlord charged unauthorized late fees.
- Paid rent after notice: No
- Applied for rental assistance: Yes, under review with UniteCT
- Written repair notice sent to landlord: Yes, sent written notice about broken heat on November 15
- Defenses to check: Numbers 4 and 10 (code violations/repairs, and additional reasons: unauthorized late fees)
- Facts for defense 4: The main heating boiler broke down in November and the landlord failed to repair it for 8 weeks despite multiple written notices.
- Facts for defense 10: The ledger includes unauthorized late fees and utility charges not allowed by the lease.
- Hardship letter: Yes, work hours cut in January and unexpected medical bills.
- Payment plan: Yes, propose $150.00 per month.
- Facing immediate lockout: No
- Motion for continuance: Yes, 30 days to await UniteCT decision and consult legal aid.
- Emergency stay: Yes, 30 days to avoid homelessness with 2 young children.
- Financial: Gross income $2,400.00/mo, currently Employed.
- Employer: Yale New Haven Health, 789 Howard Avenue, New Haven, CT 06519.
- Take-home net pay: $1,950.00/mo.
- Other regular income: None.
- Number of dependents: 2
- Monthly rent payment: $1,350.00
- Monthly utilities: $180.00
- Monthly food/grocery: $450.00
- Monthly transportation: $120.00
- Monthly medical: $60.00
- Monthly childcare: $0.00
- Monthly debt payments: $150.00
- Public assistance: Yes, SNAP and Medicaid. Other benefits: None.
- Cash on hand: $80.00
- Checking/savings balance: $150.00
- Own a vehicle: Yes, 2014 Toyota Corolla, value $4,500.00, loan balance $0.00 (paid off).
- Real estate: No.

INSTRUCTIONS FOR YOU (THE TENANT):
1. Respond to the intake specialist's latest question directly, politely, and concisely (1 short sentence or phrase).
2. Answer ONLY what is specifically asked in that single question.
3. For yes/no questions, answer with "Yes" or "No".
4. When asked which defense numbers you want to check, say "4 and 10".
5. Never invent facts outside your profile.
"""


def get_tenant_response(history: list[dict], client) -> str:
    """Simulate Sarah Jenkins answering the latest question based on her profile and conversation history."""
    # Convert conversation history to tenant's point of view:
    # assistant messages become user prompts; tenant's prior responses become assistant messages.
    tenant_messages = [{"role": "system", "content": TENANT_PERSONA}]
    for msg in history:
        if msg["role"] == "assistant":
            tenant_messages.append({"role": "user", "content": msg["content"]})
        elif msg["role"] == "user":
            tenant_messages.append({"role": "assistant", "content": msg["content"]})

    res = client.chat.completions.create(
        model="deepseek-chat",
        messages=tenant_messages,
        temperature=0.2,
        max_tokens=150,
    )
    return (res.choices[0].message.content or "").strip()


def run_two_agent_simulation():
    print("=" * 70)
    print("STARTING TWO-AGENT REAL-USER CHAT SIMULATION (CONNECTICUT)")
    print("=" * 70)

    client = _get_client()

    # The conversation from the AI intake specialist's perspective
    intake_messages = [
        {"role": "assistant", "content": (
            "Welcome! I'm your AI intake specialist for evictions.help. "
            "Please allow 10-15 minutes to answer my questions. At the end, "
            "you'll download your ready-to-file court packet immediately. "
            "Let's get started — what is your full legal name, exactly as it appears on your eviction notice or lease?"
        )}
    ]

    extracted_data = None
    max_turns = 70
    chat_errors = []

    for turn in range(1, max_turns + 1):
        latest_question = intake_messages[-1]["content"]

        # Sarah responds
        user_response = get_tenant_response(intake_messages, client)

        print(f"\n[Turn {turn}] Assistant: {latest_question[:110]}...")
        print(f"[Turn {turn}] Sarah: {user_response}")

        intake_messages.append({"role": "user", "content": user_response})

        # Intake specialist processes and asks next question
        res = get_chat_response(intake_messages, state="CT", county="New Haven")
        asst_msg = res.get("message", "")

        # Audit checks on Assistant response:
        # 1. Cross-state leakage check
        for banned in ["Colorado", "Denver", "JDF", "Section 7e", "e-filing", "E-Filing"]:
            if banned.lower() in asst_msg.lower():
                err = f"[Turn {turn}] LEAKAGE ERROR: '{banned}' appeared in assistant response!"
                print(f"  {err}")
                chat_errors.append(err)

        # 2. Strict combo question check
        q_marks = asst_msg.count("?")
        if q_marks > 1 and "ready" not in asst_msg.lower() and "which number" not in asst_msg.lower():
            warn = f"[Turn {turn}] COMBO QUESTION WARNING: {q_marks} question marks found in assistant message."
            print(f"  {warn}")

        intake_messages.append({"role": "assistant", "content": asst_msg})

        if res.get("ready_for_intake") and res.get("extracted_data"):
            extracted_data = res["extracted_data"]
            print(f"\n>>> INTAKE COMPLETE at Turn {turn}! Final JSON extracted successfully.")
            break

    if not extracted_data:
        print("\nRequesting final packet wrap-up...")
        intake_messages.append({"role": "user", "content": "That is all my information. Please generate my court packet now."})
        res = get_chat_response(intake_messages, state="CT", county="New Haven")
        extracted_data = res.get("extracted_data")

    print("\n" + "=" * 70)
    print(f"CHAT AUDIT SUMMARY: {len(chat_errors)} cross-state errors detected across {len(intake_messages)//2} turns.")
    print("=" * 70)

    return extracted_data, intake_messages


def generate_and_verify_packet(data: dict):
    print("\n" + "=" * 70)
    print("GENERATING FULL TEST PACKET FROM SIMULATED DATA")
    print("=" * 70)

    out_dir = "test_packages/CT_Sarah_Jenkins"
    os.makedirs(out_dir, exist_ok=True)
    zip_path = "test_packages/CT_Sarah_Jenkins_packet.zip"

    # Fill Answer Form (JD-HM-5)
    ans_path = os.path.join(out_dir, "01_COURT_FORM_Answer_FILE_THIS.pdf")
    ok_ans = fill_answer_form(data, "CT", ans_path)
    print(f"Fill Form JD-HM-5: {'SUCCESS' if ok_ans else 'FAILED'}")

    # Fill Fee Waiver (JD-CV-120)
    fw_path = os.path.join(out_dir, "02_COURT_FORM_Fee_Waiver_FILE_THIS.pdf")
    ok_fw = fill_fee_waiver(data, "CT", fw_path)
    print(f"Fill Form JD-CV-120: {'SUCCESS' if ok_fw else 'FAILED'}")

    # Generate supporting docs
    docs = generate_packet(data, out_dir)
    for doc_name, doc_path in docs.items():
        print(f"  {os.path.basename(doc_path)}: {os.path.getsize(doc_path):,} bytes")

    # Create ZIP archive
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, _, files in os.walk(out_dir):
            for file in sorted(files):
                full_p = os.path.join(root, file)
                rel_p = os.path.relpath(full_p, out_dir)
                zf.write(full_p, rel_p)
    print(f"\nCreated bundle ZIP: {zip_path} ({os.path.getsize(zip_path):,} bytes)")

    print("\n" + "=" * 70)
    print("VERIFYING GENERATED COURT FORMS & DOCUMENTS")
    print("=" * 70)

    # 1. Verify JD-HM-5
    doc_ans = fitz.open(ans_path)
    p1_ans = {w.field_name: w.field_value for w in doc_ans[0].widgets()}
    print("\n[JD-HM-5 Form Field Inspection]")
    print(f"  Caption:       {p1_ans.get('form1[0].FRONT[0].CASE[0]')}")
    print(f"  Docket:        {p1_ans.get('form1[0].FRONT[0].DOCKETNO[0]')}")
    print(f"  Denials (1-8): {[p1_ans.get(f'form1[0].FRONT[0].PARA{i}[1]') for i in range(1, 9)]}")
    print(f"  Box d (repairs): {p1_ans.get('form1[0].FRONT[0].NORENTDUE[0]')}")
    print(f"  Box d details: {p1_ans.get('form1[0].FRONT[0].CODEVIOLA[0]')[:65]}...")
    print(f"  Box e (notified): {p1_ans.get('form1[0].FRONT[0].NOTIFIED[0]')} (notified landlord: {p1_ans.get('form1[0].FRONT[0].NOTE[0]')})")
    print(f"  Box k (other): {p1_ans.get('form1[0].FRONT[0].ADDITIONALREASONS[0]')}")
    print(f"  Box k details: {p1_ans.get('form1[0].FRONT[0].ADDINFO[0]')[:65]}...")
    print(f"  Cert Name:     {p1_ans.get('form1[0].FRONT[0].CERTNAME[0]')}")
    print(f"  Cert Mail:     {p1_ans.get('form1[0].FRONT[0].CERTMAIL[0]')}")
    print(f"  Cert Phone:    {p1_ans.get('form1[0].FRONT[0].CERTPHONE[0]')}")
    print(f"  Cert Recipient:{repr(p1_ans.get('form1[0].FRONT[0].CERTADDR[0]'))}")
    print(f"  Cert Date:     {p1_ans.get('form1[0].FRONT[0].CERTDATE[0]')}")

    # 2. Verify JD-CV-120
    doc_fw = fitz.open(fw_path)
    p1_fw = {w.field_name: w.field_value for w in doc_fw[0].widgets()}
    print("\n[JD-CV-120 Fee Waiver Inspection]")
    print(f"  Case:            {p1_fw.get('NAMECASE[0]')}")
    print(f"  Applicant:       {p1_fw.get('topmostSubform[0].Page1[0].NAMEAPP[0]')}")
    print(f"  Court Address:   {p1_fw.get('topmostSubform[0].Page1[0].COURT[2]')}")
    print(f"  Housing Session: {p1_fw.get('topmostSubform[0].Page1[0].COURT[1]')} (TYPE: {p1_fw.get('topmostSubform[0].Page1[0].TYPE[2]')})")
    print(f"  Filing Fee:      {p1_fw.get('topmostSubform[0].Page1[0].FILING[0]')}")
    print(f"  Dependents:      {p1_fw.get('DEPENDENTS')}")
    print(f"  Gross Income:    {p1_fw.get('GMI')}")
    print(f"  Net Income:      {p1_fw.get('NMI')}")
    print(f"  Other Income:    {p1_fw.get('INCOMEOTHER')}")
    print(f"  Sources:         {p1_fw.get('topmostSubform[0].Page1[0].COLUMN1[0].SOURCE[0]')}")
    print(f"  Total Income:    {p1_fw.get('TOTALMONTHLYINCOME')}")
    print("  Expenses Schedule:")
    for i in range(1, 11):
        desc = ""
        if i == 10:
            desc = f" ({p1_fw.get('topmostSubform[0].Page1[0].COLUMN1[0].OTHEREXPENSES[0]')})"
        print(f"    ME{i}: {p1_fw.get(f'ME{i}')}{desc}")
    print(f"  Total Expenses:  {p1_fw.get('TOTALME')}")
    print(f"  Total Assets:    {p1_fw.get('TOTALASSETS')}")
    print(f"  Total Debt:      {p1_fw.get('DEBTOWEDTOTAL')} (Payment: {p1_fw.get('DEBTPAYTOTAL')})")

    p2_fw = {w.field_name: w.field_value for w in doc_fw[1].widgets()}
    print(f"  Page 2 Signer:   {p2_fw.get('topmostSubform[0].Page2[0].NAMESIGN[0]')}")
    print(f"  Page 2 Date:     {p2_fw.get('topmostSubform[0].Page2[0].DATESIGN[0]')}")

    # 3. Scan all 21 files for placeholders & leaks
    print("\n[Scanning All 21 Documents for Placeholders / Cross-State Leaks]")
    all_clean = True
    for f in sorted(os.listdir(out_dir)):
        if not f.endswith(".pdf"):
            continue
        fp = os.path.join(out_dir, f)
        doc = fitz.open(fp)
        txt = "".join(p.get_text() for p in doc)
        for leak in ["Colorado", "Denver", "JDF 205", "JDF 100", "undefined", "[Your Name]", "[Court Name]"]:
            if leak.lower() in txt.lower():
                print(f"  [LEAK] {f}: found '{leak}'")
                all_clean = False
    if all_clean:
        print("  ALL 21 DOCUMENTS ARE 100% CLEAN! Zero leaks, zero unreplaced placeholders.")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--live":
        data, history = run_two_agent_simulation()
        if data:
            with open("test_packages/simulated_ct_sarah_jenkins.json", "w") as f:
                json.dump(data, f, indent=2)
            generate_and_verify_packet(data)
        else:
            print("[!] No extracted data returned from chat.")
    elif os.path.exists("test_packages/simulated_ct_sarah_jenkins.json"):
        print("Using extracted simulation data from test_packages/simulated_ct_sarah_jenkins.json...")
        with open("test_packages/simulated_ct_sarah_jenkins.json") as f:
            data = json.load(f)
        generate_and_verify_packet(data)
    else:
        data, history = run_two_agent_simulation()
        if data:
            with open("test_packages/simulated_ct_sarah_jenkins.json", "w") as f:
                json.dump(data, f, indent=2)
            generate_and_verify_packet(data)
        else:
            print("[!] No extracted data returned from chat.")
