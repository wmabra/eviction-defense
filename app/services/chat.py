"""DeepSeek-powered chat intake service."""
import json
import os
from openai import OpenAI

# DeepSeek API config
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=DEEPSEEK_BASE_URL)

SYSTEM_PROMPT = """You are an intake specialist for Eviction Defense, a Florida self-help document preparation service. Your job is to conversationally collect the information needed to prepare eviction defense paperwork.

CRITICAL RULES:
1. Be warm, supportive, and professional. These are stressed tenants facing eviction.
2. Ask ONE question at a time. Keep it conversational.
3. Collect these required fields (in this order):
   - Full name
   - County in Florida (must be one of: Miami-Dade, Broward, Duval, Hillsborough, Orange, Palm Beach, Polk, Pinellas, Volusia, Lee, Leon, Seminole, Osceola, Pasco, Brevard)
   - Are they the tenant named in the eviction? (yes/no)
   - Is this a residential property? (yes/no)
   - Have they been served with court papers (summons and complaint)? (yes/no)
   - Has a writ of possession been issued or is the sheriff involved? (yes/no)
   - Is this Section 8 or public housing? (yes/no)
   - Are they active military? (yes/no)
   - Is there a bankruptcy involved? (yes/no)

4. If any risk flag is YES (writ/sheriff, Section 8, active military, bankruptcy), immediately explain this is beyond self-help and suggest legal aid. Do NOT collect further info.
5. If they've been served (yes) and no risk flags, tell them they're likely eligible and we'll prepare their packet for $395.
6. After collecting all info, respond with a JSON block at the end:
   ```json
   {"ready_for_eligibility": true, "collected_data": {"full_name": "...", "county": "...", ...}}
   ```
7. Never make up legal advice. If asked, say "I'm an intake specialist, not an attorney. I can help prepare your paperwork but cannot give legal advice."
8. Keep responses to 2-3 sentences maximum. Be concise but warm.
"""


def get_chat_response(messages: list[dict]) -> dict:
    """Get a response from DeepSeek for the chat intake."""
    full_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        *messages,
    ]

    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=full_messages,
        temperature=0.7,
        max_tokens=500,
    )

    content = response.choices[0].message.content

    # Try to extract JSON data block
    extracted_data = None
    ready = False
    try:
        if "```json" in content:
            json_start = content.index("```json") + 7
            json_end = content.index("```", json_start)
            json_str = content[json_start:json_end].strip()
            data = json.loads(json_str)
            ready = data.get("ready_for_eligibility", False)
            extracted_data = data.get("collected_data")
            # Remove the JSON block from the displayed message
            content = content[: content.index("```json")].strip()
    except (ValueError, json.JSONDecodeError):
        pass

    return {
        "message": content,
        "ready_for_eligibility": ready,
        "extracted_data": extracted_data,
    }
