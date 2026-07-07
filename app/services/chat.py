"""DeepSeek-powered chat intake service."""
import json
from openai import OpenAI
from app.config import settings

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

_client = None

def _get_client():
    global _client
    if _client is None:
        api_key = settings.deepseek_api_key
        _client = OpenAI(api_key=api_key, base_url=DEEPSEEK_BASE_URL)
    return _client


SYSTEM_PROMPT = """You are an intake specialist for Eviction Defense, a Florida self-help document preparation service. Your job is to conversationally collect the information needed to prepare eviction defense paperwork.

CRITICAL RULES:
1. Be warm, supportive, and professional. These are stressed tenants facing eviction.
2. Ask ONE question at a time. Keep it conversational. NEVER skip ahead — collect every field.
3. Collect these required fields (in this EXACT order):
   - Full legal name exactly as it appears on the eviction notice or lease
   - Property address being evicted from (street, city, zip)
   - County in Florida (must be one of: Miami-Dade, Broward, Duval, Hillsborough, Orange, Palm Beach, Polk, Pinellas, Volusia, Lee, Leon, Seminole, Osceola, Pasco, Brevard)
   - Do they have a copy of the eviction notice or court papers? Encourage upload if yes.
   - Landlord or company name EXACTLY as written on the eviction notice/summons
   - Case number (from the summons/complaint, if they have it)
   - Cell phone number (for SMS court date reminders)
   - Email address (to receive the completed packet)
   - Are they the tenant named in the eviction? (yes/no)
   - Is this a residential property? (yes/no)
   - Have they been served with court papers (summons and complaint)? (yes/no)
   - Has a writ of possession been issued or is the sheriff involved? (yes/no)
   - Is this Section 8 or public housing? (yes/no)
   - Are they active military? (yes/no)
   - Is there a bankruptcy involved? (yes/no)

4. If any risk flag is YES (writ/sheriff, Section 8, active military, bankruptcy), immediately explain this is beyond self-help and suggest legal aid. Do NOT collect further info.
5. If they've been served (yes) and no risk flags, tell them they're likely eligible and a $395 packet includes: official court answer form, filing checklist, court hearing guide, landlord letter, rental assistance list, SMS reminders.
6. After collecting ALL fields above, respond with a JSON block at the end:
   {"ready_for_eligibility": true, "collected_data": {"full_name": "...", "county": "...", "property_address": "...", "landlord_name": "...", "case_number": "...", "is_tenant": true, "is_residential": true, "received_court_papers": true, "has_eviction_notice": true}}
7. Never make up legal advice. If asked, say "I'm an intake specialist, not an attorney. I can help prepare your paperwork but cannot give legal advice."
8. Keep responses to 2-3 sentences maximum. Be concise but warm.
"""


def get_chat_response(messages: list[dict]) -> dict:
    """Get a response from DeepSeek for the chat intake."""
    full_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    client = _get_client()
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=full_messages,
        temperature=0.7,
        max_tokens=500,
    )

    content = response.choices[0].message.content

    extracted_data = None
    ready = False
    try:
        if "{" in content and "ready_for_eligibility" in content:
            json_start = content.index("{")
            json_end = content.rindex("}") + 1
            json_str = content[json_start:json_end].strip()
            data = json.loads(json_str)
            ready = data.get("ready_for_eligibility", False)
            extracted_data = data.get("collected_data")
            content = content[:json_start].strip()
    except (ValueError, json.JSONDecodeError):
        pass

    return {
        "message": content,
        "ready_for_eligibility": ready,
        "extracted_data": extracted_data,
    }
