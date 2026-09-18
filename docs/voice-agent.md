# Voice Agent ("Eva") — setup & operations

The phone support agent for evictions.help. Answers the number
**+1-561-960-0485**, is named **Eva**, and runs on **Retell AI** with the call
routed through **Telnyx** SIP. Its tool calls hit this repo's FastAPI backend at
`/api/v1/voice/*`.

## Architecture

```text
Caller → +15619600485 → Telnyx (FQDN connection) → sip.retellai.com:5060
       → Retell → agent "Eva" → tools → evictions.help/api/v1/voice/*
```

- **Retell LLM** (`response_engine`) holds the system prompt + tools.
- **Retell agent** holds the voice, webhook, and behavior knobs, and points at the LLM.
- **Telnyx** provides the number and SIP trunk to Retell.

### Key identifiers (not secrets)

| Thing | Value |
|-------|-------|
| Retell agent id | `agent_da5bed14bd28679f83d072cd33` |
| Retell LLM id (gpt-4.1) | `llm_87dab7937936a2b60db4da926390` |
| Voice | `retell-Willa` |
| Phone number | `+15619600485` |
| Telnyx FQDN connection | `Eva Voice Agent - evictions.help` |
| Telnyx FQDN object | `sip.retellai.com` port `5060` |

## Files

- `app/services/voice_prompt.md` — the agent's system prompt ("the brain").
- `scripts/deploy_voice_agent.py` — pushes prompt + tools to Retell (LLM + agent).
- `scripts/import_telnyx_number.py` — imports the Telnyx number into Retell.
- `app/routers/voice.py` — `/api/v1/voice/*` endpoints (verify, package, document-help, correction, ticket, resend, webhook, callback).
- `app/database/models.py` — `CallLog` model (persists call outcome/transcript/analysis).
- `.github/workflows/deploy.yml` — manual-only backend deploy (verify-first).

## One-time setup (already done — reference only)

1. **Deploy the agent** — `python scripts/deploy_voice_agent.py`
   (updates the Retell LLM's `general_prompt` + 8 tools + `begin_message`, and the
   agent's voice/webhook/behavior).

2. **Publish the agent** — Retell agents only take calls on a published version:

   ```text
   POST https://api.retellai.com/publish-agent-version/{agent_id}
   {"version": 0}
   ```

3. **Telnyx SIP trunk** (two resources — the FQDN is a *separate object*):

   ```text
   POST /v2/fqdn_connections   {connection_name, transport_protocol: "UDP"}
   POST /v2/fqdns              {connection_id, fqdn: "sip.retellai.com", port: 5060, dns_record_type: "a"}
   PATCH /v2/phone_numbers/+15619600485  {connection_id}
   ```

   ⚠️ Gotcha: Telnyx ignores `fqdn`/`sip_transport`/`sip_port` on the *connection* —
   the routing target lives on the separate FQDN object, referenced by the
   connection's `inbound.default_primary_fqdn_id`.

4. **Retell import + bind**:

   ```text
   POST  /import-phone-number
     {phone_number, termination_uri: "sip.telnyx.com", transport: "UDP",
      sip_trunk_auth_username, sip_trunk_auth_password}

   PATCH /update-phone-number/+15619600485
     {inbound_agents: [{agent_id, weight: 1}], outbound_agents: [{agent_id, weight: 1}]}
   ```

   - `termination_uri` = Telnyx's SIP FQDN (for **outbound** Retell→Telnyx).
   - `sip.retellai.com` is Retell's **inbound** SIP address (provider → Retell).

## Environment (.env — values omitted)

```text
RETELL_API_KEY=          RETELL_LLM_ID=   RETELL_VOICE_ID=retell-Willa
RETELL_AGENT_ID=         TELNYX_API_KEY=  TELNYX_PHONE_NUMBER=+15619600485
VOICE_APP_URL=https://evictions.help    # public URL Retell's tools call
```

## Day-to-day operations

**Update the agent (prompt / tools / voice):**

1. Edit `app/services/voice_prompt.md` (and/or the tools in `deploy_voice_agent.py`).
2. `python scripts/deploy_voice_agent.py` — updates the Retell LLM + agent.
3. If the agent config changed, re-publish:
   `POST /publish-agent-version/{agent_id} {"version": 0}`.

**Deploy backend code (voice.py, models, etc.):**

1. Verify locally: `pytest -q`, `tests/check_all_overlap.py`, `tests/verify_editable_fields.py`.
2. Commit + push (push does **not** auto-deploy).
3. `gh workflow run deploy.yml` (manual, verify-first).

**Call outcomes** land in the `call_logs` table (via `/webhook`) — transcript,
outcome, duration, and post-call analysis (`call_summary`, `call_successful`,
`user_sentiment`, `customer_name`, `case_id`, `issue_summary`).

## Gotchas

- Retell stores `general_prompt` / `general_tools` / `begin_message` on the **LLM**,
  not the agent. `deploy_voice_agent.py` updates both.
- Retell voice presets (`call_summary`, `call_successful`, `user_sentiment`) were
  rejected by the API in this project's schema — use custom `string`/`boolean`/`enum`
  types in `post_call_analysis_data` instead.
- No live call transfers — unresolved issues go to a same-day callback via the
  `/callback` endpoint (emails `support@evictions.help` with name, confirmed number,
  best time, and a conversation summary).
