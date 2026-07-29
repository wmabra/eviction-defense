#!/usr/bin/env python3
"""Telnyx + Retell AI Setup Script.

Configures Telnyx elastic SIP trunking to route calls to Retell's SIP endpoint.
Run after setting TELNYX_API_KEY in .env.

Usage:
    python scripts/setup_telnyx.py

References:
    https://docs.retellai.com/integrations/sip/telnyx
"""
import os
import sys
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TELNYX_API_BASE = "https://api.telnyx.com/v2"

# Retell SIP endpoint (fixed — calls route here)
RETELL_SIP_URI = "sip:sip.retellai.com"
RETELL_SIP_USER = ""  # leave empty unless Retell provides specific creds


def telnyx_request(method, path, data=None, api_key=None):
    """Make a Telnyx API request."""
    key = api_key or os.environ.get("TELNYX_API_KEY", "")
    if not key:
        print("ERROR: TELNYX_API_KEY not set. Add it to .env first.")
        sys.exit(1)

    url = f"{TELNYX_API_BASE}{path}"
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    body = json.dumps(data).encode() if data else None
    req = Request(url, data=body, headers=headers, method=method)

    try:
        with urlopen(req) as resp:
            return json.loads(resp.read())
    except HTTPError as e:
        error_body = e.read().decode()
        print(f"  API error {e.code}: {error_body[:300]}")
        return None


def setup_telnyx():
    """Main setup flow."""
    api_key = os.environ.get("TELNYX_API_KEY", "")

    if not api_key:
        api_key = input("Enter your Telnyx API key: ").strip()
        if not api_key:
            print("No API key provided. Exiting.")
            sys.exit(1)

    print("=" * 60)
    print("  Telnyx + Retell AI — SIP Trunk Setup")
    print("=" * 60)

    # ── Step 1: Create SIP connection ──────────────────────────
    print("\n[1/4] Creating SIP connection to Retell...")

    result = telnyx_request("POST", "/sip_connections", {
        "connection_name": "Retell AI - evictions.help",
        "sip_uri": "sip.retellai.com",
        "sip_transport": "TLS",
        "sip_port": 5061,
        "codecs": ["G722", "PCMU", "PCMA"],
        "dtmf_type": "RFC2833",
        "enable_t38": False,
        "fax_failover_enabled": False,
    }, api_key=api_key)

    if not result:
        print("  Failed to create SIP connection. Check your API key.")
        sys.exit(1)

    connection_id = result.get("data", {}).get("id", "")
    print(f"  ✅ SIP connection created: {connection_id}")

    # ── Step 2: Find or create outbound voice profile ──────────
    print("\n[2/4] Configuring outbound voice profile...")

    profiles = telnyx_request("GET", "/outbound_voice_profiles", api_key=api_key)
    if profiles and profiles.get("data"):
        profile_id = profiles["data"][0]["id"]
        print(f"  Using existing profile: {profile_id}")
    else:
        print("  No existing profile, creating one...")
        profile = telnyx_request("POST", "/outbound_voice_profiles", {
            "name": "evictions.help Voice Agent",
            "traffic_type": "conversational",
            "service_plan": "global",
        }, api_key=api_key)
        profile_id = profile["data"]["id"] if profile else ""
        print(f"  Created profile: {profile_id}")

    # ── Step 3: Search and purchase toll-free number ───────────
    print("\n[3/4] Searching for toll-free numbers...")

    numbers = telnyx_request("GET", (
        "/available_phone_numbers"
        "?filter[phone_number][starts_with]=844"
        "&filter[voice]=true"
        "&filter[best_effort]=true"
        "&filter[limit]=10"
    ), api_key=api_key)

    if not numbers or not numbers.get("data"):
        print("  No 844 numbers available. Trying 833...")
        numbers = telnyx_request("GET", (
            "/available_phone_numbers"
            "?filter[phone_number][starts_with]=833"
            "&filter[voice]=true"
            "&filter[best_effort]=true"
            "&filter[limit]=10"
        ), api_key=api_key)

    if not numbers or not numbers.get("data"):
        print("  ❌ No toll-free numbers available. Purchase one in the Telnyx portal.")
        phone_number = ""
    else:
        # Pick the first available and present options
        available = [n["phone_number"] for n in numbers["data"]]
        print(f"  Available: {', '.join(available)}")
        phone_number = available[0]

        # Purchase (auto-pick first one)
        purchase = telnyx_request("POST", "/number_orders", {
            "phone_numbers": [{"phone_number": phone_number}],
            "connection_id": connection_id,
        }, api_key=api_key)

        if purchase:
            print(f"  ✅ Number ordered: {phone_number}")
        else:
            print(f"  ⚠️  Order pending — number: {phone_number}")

    # ── Step 4: Summary ───────────────────────────────────────
    print("\n" + "=" * 60)
    print("  SETUP SUMMARY")
    print("=" * 60)
    print(f"  SIP Connection ID:  {connection_id}")
    print(f"  Voice Profile ID:   {profile_id}")
    print(f"  Phone Number:       {phone_number or 'Purchase manually in Telnyx portal'}")
    print(f"  Retell SIP URI:     {RETELL_SIP_URI}:5061")
    print()
    print("  Add to .env:")
    print(f"  TELNYX_API_KEY=your-key")
    print(f"  TELNYX_PHONE_NUMBER={phone_number}")
    print()
    print("  Next step: In the Retell dashboard, go to")
    print("  Channels → SIP Trunk → Add SIP Trunk")
    print(f"  and enter the Telnyx connection details above.")

    # ── Save results ─────────────────────────────────────────
    if phone_number:
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env"
        )
        if os.path.exists(env_path):
            with open(env_path, "a") as f:
                f.write(f"\n# Telnyx\nTELNYX_PHONE_NUMBER={phone_number}\n")
            print(f"\n  ✅ Phone number saved to {env_path}")


if __name__ == "__main__":
    setup_telnyx()
