#!/usr/bin/env python3
"""Import the Telnyx number (+1-561-960-0485) into Retell and bind it to Eva.

The elastic SIP trunk must be created first in the Retell dashboard
(Channels → SIP Trunk → Elastic / "Create SIP trunk", FQDN type). That gives
three values this script needs:

  termination_uri         — e.g. xxxxx.sip.retellai.com  (the trunk FQDN)
  sip_trunk_auth_username — the SIP auth username
  sip_trunk_auth_password — the SIP auth password

Provide them via .env, environment, or flags. The phone number is imported in
E.164 format and bound to the voice agent (RETELL_AGENT_ID).

Usage:
  python scripts/import_telnyx_number.py \
      --termination-uri xxxxx.sip.retellai.com \
      --username <user> --password <pass> \
      [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

RETELL_API_BASE = "https://api.retellai.com"
DEFAULT_PHONE = "+15619600485"
DEFAULT_AGENT_ID = "agent_da5bed14bd28679f83d072cd33"  # Eva
REPO_ROOT = Path(__file__).resolve().parent.parent


def load_dotenv(path: str | Path = ".env") -> dict:
    env: dict = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def get_setting(name: str, cli: str | None, env: dict, default: str = "") -> str:
    import os
    return cli or os.environ.get(name) or env.get(name) or default


def _post(path: str, token: str, body: dict) -> Any:
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        f"{RETELL_API_BASE}{path}", data=data,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        print(f"ERROR {exc.code}: {exc.read().decode()[:500]}")
        sys.exit(1)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Import the Telnyx number into Retell.")
    p.add_argument("--termination-uri", dest="termination_uri", default="")
    p.add_argument("--username", dest="username", default="")
    p.add_argument("--password", dest="password", default="")
    p.add_argument("--phone", dest="phone", default=DEFAULT_PHONE)
    p.add_argument("--agent-id", dest="agent_id", default=DEFAULT_AGENT_ID)
    p.add_argument("--transport", dest="transport", default="TLS")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args(argv)

    env = load_dotenv(REPO_ROOT / ".env")
    token = get_setting("RETELL_API_KEY", None, env)
    termination_uri = get_setting("RETELL_SIP_TERMINATION_URI", args.termination_uri, env)
    username = get_setting("RETELL_SIP_AUTH_USERNAME", args.username, env)
    password = get_setting("RETELL_SIP_AUTH_PASSWORD", args.password, env)

    if not token:
        print("ERROR: RETELL_API_KEY is not set.")
        return 1
    if not termination_uri:
        print("ERROR: --termination-uri (or RETELL_SIP_TERMINATION_URI) is required.")
        print("       Create the elastic SIP trunk in the Retell dashboard first.")
        return 1

    body = {
        "phone_number": args.phone,
        "termination_uri": termination_uri,
        "sip_trunk_auth_username": username,
        "sip_trunk_auth_password": password,
        "transport": args.transport,
        "agent_id": args.agent_id,
    }

    if args.dry_run:
        safe = {k: ("***" if "password" in k else v) for k, v in body.items()}
        print("DRY RUN — body:")
        print(json.dumps(safe, indent=2))
        return 0

    print(f"Importing {args.phone} → agent {args.agent_id} (trunk {termination_uri})…")
    result = _post("/import-phone-number", token, body)
    print("✅ Imported:", json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
