#!/usr/bin/env python3
"""Deploy the evictions.help phone agent (system prompt + tools) to Retell AI.

Reads ``app/services/voice_prompt.md`` as the agent's system prompt, defines the
custom function tools that map 1:1 to the endpoints in ``app/routers/voice.py``,
and creates or updates the Retell voice agent through the Retell API.

This script is intentionally dependency-free (stdlib only) so it can be run on
any host that has the repo checked out — no pip install needed.

------------------------------------------------------------------------
Usage
------------------------------------------------------------------------
    python scripts/deploy_voice_agent.py                    # update (or create) the agent
    python scripts/deploy_voice_agent.py --create           # force-create a NEW agent
    python scripts/deploy_voice_agent.py --dry-run          # print the payload, no network
    python scripts/deploy_voice_agent.py --list             # list existing agents
    python scripts/deploy_voice_agent.py --get [AGENT_ID]   # dump current agent config
    python scripts/deploy_voice_agent.py --agent-id <id>    # update a specific agent

Configuration (checked in order: CLI flag > environment > .env file):
    RETELL_API_KEY     (required)  Retell API key
    RETELL_AGENT_ID    (optional)  existing agent id to update
    RETELL_LLM_ID      (optional)  default llm_87dab7937936a2b60db4da926390
    RETELL_VOICE_ID    (optional)  voice to use (default below)
    APP_URL            (optional)  default https://evictions.help
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any
from urllib.error import HTTPError

RETELL_API_BASE = "https://api.retellai.com"

DEFAULT_LLM_ID = "llm_87dab7937936a2b60db4da926390"
# NOTE: pick a warm female voice for "Eva". Retell/cartesia/minimax/elevenlabs
# voice IDs are supported. Override with RETELL_VOICE_ID or --voice-id.
DEFAULT_VOICE_ID = "retell-Cimo"
DEFAULT_APP_URL = "https://evictions.help"

# Resolve the prompt relative to the repo root (this script lives in scripts/).
REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_PROMPT_PATH = REPO_ROOT / "app" / "services" / "voice_prompt.md"

# The opening line must match the "## Opening" section of voice_prompt.md so the
# greeting and the mandatory compliance disclosure are identical on every call.
BEGIN_MESSAGE = (
    "Hi, and thanks for calling evictions.help. This is Eva. Just so you know, "
    "I'm an AI assistant, and evictions.help is a self-help document preparation "
    "service — we are not a law firm, we don't provide legal advice, and we "
    "don't represent anyone in court. How can I help you today?"
)

AGENT_NAME = "Eva — evictions.help support"


# ─────────────────────────────────────────────────────────────────────────────
# Environment helpers
# ─────────────────────────────────────────────────────────────────────────────

def load_dotenv(path: str | Path = ".env") -> dict:
    """Parse a simple KEY=VALUE .env file (no substitutions, no quotes magic).

    os.environ always wins over the file so a shell export can override a file
    value without editing the file.
    """
    env: dict = {}
    p = Path(path)
    if not p.exists():
        return env
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            env[key] = value
    return env


def get_setting(name: str, cli_value: str | None, env: dict, default: str = "") -> str:
    """Resolve a setting: CLI flag > process env > .env file > default."""
    return (
        cli_value
        or os.environ.get(name)
        or env.get(name)
        or default
    )


# ─────────────────────────────────────────────────────────────────────────────
# HTTP (stdlib urllib with retry + backoff)
# ─────────────────────────────────────────────────────────────────────────────

class RetellError(Exception):
    """Raised for any Retell API failure with a human-readable message."""


def _request(method: str, path: str, token: str, body: dict | None = None,
             retries: int = 3, timeout: int = 30) -> Any:
    """Make a Retell API call with exponential backoff and clear error parsing."""
    url = f"{RETELL_API_BASE}{path}"
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    last_err: Exception | None = None
    for attempt in range(1, retries + 1):
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except OSError as exc:
            # HTTPError, URLError, TimeoutError are all OSError subclasses.
            if isinstance(exc, HTTPError):
                try:
                    detail = json.loads(exc.read().decode("utf-8"))
                except ValueError:
                    detail = {}
                msg = detail.get("message") or detail.get("detail") or str(exc)
                err = RetellError(f"Retell API {exc.code} on {method} {path}: {msg}")
                # 4xx errors are not transient — don't retry.
                if 400 <= exc.code < 500:
                    raise err
                last_err = err
            else:
                last_err = exc

        if attempt < retries:
            wait = 2 ** attempt  # 2s, 4s, 8s...
            print(f"    ⚠️  attempt {attempt} failed ({last_err}); retrying in {wait}s")
            time.sleep(wait)

    raise RetellError(f"Retell API call failed after {retries} attempts: {last_err}")


# ─────────────────────────────────────────────────────────────────────────────
# Tool (custom function) definitions — must mirror app/routers/voice.py
# ─────────────────────────────────────────────────────────────────────────────

def _tool(name, description, parameters, path, speak_during=True,
          speak_after=True, execution_message="One moment..."):
    """Build one Retell custom-tool definition."""
    return {
        "type": "custom",
        "name": name,
        "description": description,
        "parameters": parameters,
        "url": f"{DEFAULT_APP_URL}/api/v1/voice/{path}",
        "speak_during_execution": speak_during,
        "speak_after_execution": speak_after,
        "execution_message_description": execution_message,
    }


def build_tools(app_url: str) -> list:
    """Return the full list of voice-agent tools.

    Every tool POSTs JSON to a /api/v1/voice/* endpoint. The endpoints return
    {"compliance": "...", ...} and the agent is instructed to read the payload
    and re-phrase it in a warm, plain-English voice response.
    """
    base = app_url.rstrip("/")
    return [
        _tool(
            "verify_caller",
            "Verify a caller who says they already purchased a packet, using "
            "their email address OR case ID (optionally their last 4 phone "
            "digits for extra security). Returns their case context: name, case "
            "id, status, whether the packet is ready, fee-waiver status, filing "
            "deadline, and court date. Call this BEFORE answering any "
            "post-sale question about their order.",
            {
                "type": "object",
                "properties": {
                    "email": {"type": "string", "description": "Email used at checkout."},
                    "case_id": {"type": "string", "description": "Case ID from the confirmation email."},
                    "last_four_phone": {"type": "string", "description": "Last 4 digits of the phone number on the order (optional)."},
                },
            },
            "verify",
            execution_message="Looking up your order…",
        ),
        _tool(
            "get_package",
            "Get the full packet context for an already-verified case: the list "
            "of documents in their packet, how many defenses were selected, fee "
            "waiver status, filing deadline, court name, and landlord name.",
            {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "The verified case ID."},
                },
                "required": ["case_id"],
            },
            "package",
            execution_message="Pulling up your packet…",
        ),
        _tool(
            "explain_document",
            "Explain a specific document in the caller's packet — what it is, its "
            "purpose, where to sign, and where to file.",
            {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "The verified case ID."},
                    "doc_name": {"type": "string", "description": "The document name the caller is asking about (e.g. 'answer form' or 'fee waiver')."},
                },
                "required": ["case_id", "doc_name"],
            },
            "document-help",
            execution_message="Looking that document up…",
        ),
        _tool(
            "request_correction",
            "Log a correction request when the caller reports a mistake in their "
            "packet (wrong name, address, case number, date, amount, etc.). Our "
            "team reviews it and sends an updated packet, usually within one "
            "business day.",
            {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "The verified case ID."},
                    "field_or_document": {"type": "string", "description": "Which field or document is wrong."},
                    "description": {"type": "string", "description": "What needs to change."},
                    "caller_email": {"type": "string", "description": "Email to send the updated packet to."},
                },
                "required": ["case_id", "field_or_document", "description", "caller_email"],
            },
            "correction",
            execution_message="Recording that for our team…",
        ),
        _tool(
            "create_ticket",
            "Create a support ticket for human follow-up for a billing, "
            "correction, technical, or other issue you cannot resolve.",
            {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "Case ID if available, else empty string."},
                    "caller_name": {"type": "string"},
                    "caller_email": {"type": "string"},
                    "caller_phone": {"type": "string"},
                    "issue_type": {"type": "string", "enum": ["billing", "correction", "technical", "other"]},
                    "description": {"type": "string", "description": "A clear summary of the issue."},
                },
                "required": ["issue_type", "description"],
            },
            "ticket",
            execution_message="Creating a support ticket…",
        ),
        _tool(
            "resend_packet",
            "Resend the packet download link to the caller's email.",
            {
                "type": "object",
                "properties": {
                    "case_id": {"type": "string", "description": "The verified case ID."},
                    "email": {"type": "string", "description": "Email to resend to (optional if case_id is known)."},
                },
            },
            "resend",
            execution_message="Resending your packet…",
        ),
        _tool(
            "request_callback",
            "Set up a same-day callback when the caller needs a human (we do NOT "
            "do live transfers). Collect their name, phone, best time (Eastern), "
            "and a short issue summary; it emails support@evictions.help.",
            {
                "type": "object",
                "properties": {
                    "first_name": {"type": "string"},
                    "last_name": {"type": "string"},
                    "phone": {"type": "string", "description": "Best callback phone number."},
                    "best_time_eastern": {"type": "string", "description": "e.g. 'between 2pm and 4pm'."},
                    "case_id": {"type": "string", "description": "Case ID if available."},
                    "issue_summary": {"type": "string", "description": "Short description of what they need help with."},
                    "caller_email": {"type": "string"},
                },
                "required": ["first_name", "last_name", "phone", "best_time_eastern", "issue_summary"],
            },
            "callback",
            execution_message="Setting up your callback…",
        ),
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Agent payload
# ─────────────────────────────────────────────────────────────────────────────

def build_payload(prompt: str, llm_id: str, voice_id: str, app_url: str,
                  begin_message: str, agent_name: str) -> dict:
    """Build the Retell agent body (create-agent / update-agent)."""
    return {
        "agent_name": agent_name,
        "response_engine": {
            "type": "retell-llm",
            "llm_id": llm_id,
            "version": 0,
        },
        "voice_id": voice_id,
        "language": "en-US",
        "general_prompt": prompt,
        "begin_message": begin_message,
        "general_tools": build_tools(app_url),
        # Post-call logging back into this app (voice.py /webhook).
        "webhook_url": f"{app_url.rstrip('/')}/api/v1/voice/webhook",
        "webhook_events": ["call_ended", "call_analyzed"],
        # Keep the model on-topic (see voice_prompt.md "Out-of-Scope Topics").
        "boosted_keywords": [
            "eviction", "evictions.help", "answer form", "fee waiver",
            "filing deadline", "court date", "landlord", "packet", "file",
        ],
        "end_call_after_silence_ms": 600000,   # 10 min of silence → hang up
        "max_call_duration_ms": 1800000,       # 30 min hard cap
        "reminder_trigger_ms": 10000,
        "reminder_message": "Are you still there?",
        "responsiveness": 0.6,
        "interruption_sensitivity": 0.5,
        "voice_speed": 1.0,
        "voice_temperature": 1.0,
        "ambient_sound": "coffee-shop",
        "enable_backchannel": True,
        "backchannel_words": ["yeah", "uh-huh", "got it"],
        "data_storage_setting": "everything",
    }


# ─────────────────────────────────────────────────────────────────────────────
# Retell operations
# ─────────────────────────────────────────────────────────────────────────────

def create_agent(token: str, payload: dict) -> dict:
    return _request("POST", "/create-agent", token, payload)


def update_agent(token: str, agent_id: str, payload: dict) -> dict:
    return _request("PATCH", f"/update-agent/{agent_id}", token, payload)


def get_agent(token: str, agent_id: str) -> dict:
    return _request("GET", f"/get-agent/{agent_id}", token)


def list_agents(token: str) -> list:
    return _request("GET", "/list-agents", token)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def _redact(text: str, secrets: list[str]) -> str:
    for s in secrets:
        if s:
            text = text.replace(s, "***")
    return text


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deploy the evictions.help phone agent to Retell AI.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--create", action="store_true",
                        help="Force-create a new agent (ignore RETELL_AGENT_ID).")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the payload and exit without any network call.")
    parser.add_argument("--list", action="store_true", help="List existing agents.")
    parser.add_argument("--get", nargs="?", const="", metavar="AGENT_ID",
                        help="Print the current config for AGENT_ID (or RETELL_AGENT_ID).")
    parser.add_argument("--agent-id", dest="agent_id", default="",
                        help="Agent ID to update (overrides RETELL_AGENT_ID).")
    parser.add_argument("--voice-id", dest="voice_id", default="",
                        help="Voice to use (overrides RETELL_VOICE_ID).")
    parser.add_argument("--llm-id", dest="llm_id", default="",
                        help="Retell LLM id (overrides RETELL_LLM_ID).")
    parser.add_argument("--app-url", dest="app_url", default="",
                        help="Public app base URL (overrides APP_URL).")
    parser.add_argument("--prompt-file", dest="prompt_file", default=str(DEFAULT_PROMPT_PATH),
                        help="Path to the system prompt markdown.")
    args = parser.parse_args(argv)

    env = load_dotenv(REPO_ROOT / ".env")
    token = get_setting("RETELL_API_KEY", None, env)
    llm_id = get_setting("RETELL_LLM_ID", args.llm_id, env, DEFAULT_LLM_ID)
    voice_id = get_setting("RETELL_VOICE_ID", args.voice_id, env, DEFAULT_VOICE_ID)
    app_url = get_setting("APP_URL", args.app_url, env, DEFAULT_APP_URL).rstrip("/")
    env_agent_id = get_setting("RETELL_AGENT_ID", None, env)
    agent_id = args.agent_id or env_agent_id

    # --list / --get don't need the prompt or a payload.
    if args.list:
        if not token:
            print("ERROR: RETELL_API_KEY is not set (put it in .env or export it).")
            return 1
        print("Listing agents…")
        agents = list_agents(token)
        for a in agents:
            print(f"  {a.get('agent_id')}  {a.get('agent_name')}")
        return 0

    if args.get is not None:
        target = args.get or agent_id
        if not target:
            print("ERROR: no agent id — pass --get <id> or set RETELL_AGENT_ID.")
            return 1
        if not token:
            print("ERROR: RETELL_API_KEY is not set.")
            return 1
        cfg = get_agent(token, target)
        print(json.dumps(cfg, indent=2))
        return 0

    # Everything below needs the prompt + a payload.
    if not token:
        print("ERROR: RETELL_API_KEY is not set (put it in .env or export it).")
        print("       Get it from the Retell dashboard → API Keys.")
        return 1

    prompt_path = Path(args.prompt_file)
    if not prompt_path.exists():
        print(f"ERROR: prompt file not found: {prompt_path}")
        print("       Point --prompt-file at the system prompt markdown.")
        return 1
    prompt = prompt_path.read_text(encoding="utf-8").strip()
    if not prompt:
        print(f"ERROR: prompt file is empty: {prompt_path}")
        return 1

    payload = build_payload(prompt, llm_id, voice_id, app_url, BEGIN_MESSAGE, AGENT_NAME)

    if args.dry_run:
        secrets = [token]
        safe = json.dumps(payload, indent=2)
        print("DRY RUN — no network call. Payload:")
        print(_redact(safe, secrets))
        print(f"\nWould {'CREATE' if args.create or not agent_id else 'UPDATE'} agent "
              f"{'(new)' if args.create or not agent_id else agent_id}.")
        return 0

    if args.create or not agent_id:
        print(f"Creating new agent (voice={voice_id}, llm={llm_id})…")
        result = create_agent(token, payload)
        new_id = result.get("agent_id", "")
        print(f"✅ Created agent {new_id}")
        if new_id:
            print(f"   Save it: RETELL_AGENT_ID={new_id}  (add to .env to make "
                  f"future runs update instead of create)")
        return 0

    print(f"Updating agent {agent_id} (voice={voice_id}, llm={llm_id})…")
    result = update_agent(token, agent_id, payload)
    print(f"✅ Updated agent {result.get('agent_id', agent_id)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
