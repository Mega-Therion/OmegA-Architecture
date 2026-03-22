# Security and Privacy Specification
**Version:** 1.0.0
**Status:** CANONICAL
**Last Updated:** 2026-03-13
**Operator:** RY (Mega)

This document defines OmegA's security architecture, authentication model, secrets handling, and incident response procedures. Synthesized from LAW.json, the Rust gateway security audit (CLAUDE_AUDIT_REPORT.md), and system architecture.

---

## 1. Threat Model

### Assets to Protect
- API keys and bearer tokens (Anthropic, OpenAI, Google, Perplexity, DeepSeek, Grok, Supabase, Telegram)
- Supabase project credentials and URLs
- OmegA identity (from provider contamination / adversarial injection)
- Memory contents (especially L6 Phylactery / canon facts)
- Host filesystem (especially restricted paths)

### Threat Actors
- **External attackers:** Unauthorized API access attempting to use OmegA as an LLM proxy
- **Prompt injection:** Adversarial input attempting to override OmegA identity or extract system prompts
- **Provider identity bleed:** LLM responses that embed provider identity signals (Claude/GPT/Gemini phrasing)
- **Runaway automation:** OmegA-initiated actions that exceed intended scope
- **Configuration drift:** Secrets leaking into logs, commits, or public-facing endpoints

### Non-Threats (Out of Scope)
- Physical hardware access to the host machine (RY controls this)
- Nation-state attacks (out of scale for current deployment)
- Multi-tenant isolation (single-operator system)

---

## 2. Authentication Architecture

### Bearer Token Authentication (Gateway)

The Rust gateway enforces bearer token auth for all `/api/v1/*` endpoints.

**Token source:** `OMEGA_API_BEARER_TOKEN` environment variable
- Set in: `~/NEXUS/OmegA/OmegA-SI/services/trinity/gateway/one-true.env`
- Synced via: `scripts/sync-gateway-env.sh --apply`

**Behavior:**
- Empty `OMEGA_API_BEARER_TOKEN` → permissive mode (development only)
- Non-empty token → enforced; requests without correct token are rejected
- Missing `Authorization` header → 401 Unauthorized
- Wrong token value → 403 Forbidden

**Auth middleware location:** `rust/omega-rust/crates/omega-gateway/src/middleware/policy.rs`

### API Key Handling

All provider API keys use the `OMEGA_` prefix in environment variables:
- `OMEGA_ANTHROPIC_API_KEY`
- `OMEGA_OPENAI_API_KEY`
- `OMEGA_GEMINI_API_KEY`
- `OMEGA_PERPLEXITY_API_KEY`
- `OMEGA_DEEPSEEK_API_KEY`
- `OMEGA_GROK_API_KEY`

Master credentials file: `~/.omega/vault/master.env` (never committed to git)

Keys are loaded via pydantic `env_prefix="OMEGA_"` (Python gateway config) and Figment (Rust gateway config). Never hardcoded in source.

**Audit confirmation (2026-03-08):** Zero hardcoded API keys, tokens, or secrets found across all Rust source files. All secrets come from env vars. ✓

---

## 3. What NEVER Goes in Logs

The following must NEVER appear in any log output, trace, or audit trail:

- API keys (any `OMEGA_*_API_KEY` value)
- Bearer token values
- Supabase connection strings with credentials
- JWT secrets
- Personal credentials of any kind
- Raw `Authorization` header contents
- Telegram bot tokens
- Database passwords

**Enforcement in Rust gateway (verified 2026-03-08):**
- Auth middleware logs "Missing bearer token" and "Invalid bearer token" — token value is never logged
- Provider errors log status codes and error messages, not request headers
- No `tracing::` calls emit key values

**Development rule:** Never use `console.log()`, `print()`, or `tracing::` to debug auth values. Use masked representations (`***`, `[REDACTED]`) if logging around sensitive operations.

---

## 4. Sensitive Path Restrictions

From `LAW.json` restricted_folders:

| Path | Restriction |
|------|-------------|
| `/etc` | No read or write without explicit operator consent |
| `/usr/bin` | No modification |
| `/boot` | No modification |
| `/root` | No access |
| `/var/log/auth.log` | No read (auth log privacy) |

**`agentic-fs` tool:** All filesystem tool operations are path-validated against `AGENTIC_ROOT`. Paths outside `AGENTIC_ROOT` are blocked unless the operator grants explicit consent.

---

## 5. Command Blocklist

From `LAW.json` command_blocklist — OmegA must never execute these commands:

| Command | Risk |
|---------|------|
| `rm -rf /` | Full filesystem destruction |
| `mkfs` | Filesystem formatting |
| `dd if=/dev/zero` | Disk wiping |
| `chmod -R 777` | Universal permission grant |
| `chown -R` | Mass ownership change |

**From forbidden_actions (LAW.json):**
- `delete_os_kernel`
- `rm_root_recursive`
- `broadcast_raw_secrets`
- `shutdown_host_without_permission`
- `modify_security_firewall`
- `install_unauthorized_backdoors`
- `disable_risk_governor`

These are enforced at the Gateway policy middleware level before requests reach the LLM. They also apply to all tool executions in the Brain Tool Registry.

---

## 6. Rationale for Key Rules

- **No secrets in logs:** Logs are often shipped to external services, read by multiple team members, and stored longer than intended. A secret in a log is a secret at rest in an uncontrolled location.
- **Restricted paths:** The system must not be able to accidentally or adversarially modify OS configuration, authentication state, or boot sequences.
- **Command blocklist:** These commands are irreversible and catastrophic. There is no legitimate automated use case for `rm -rf /` that cannot be handled with a scoped alternative.
- **No `disable_risk_governor`:** The risk governor is the last safety layer. An agent that can disable its own governor is an agent that can do anything.

---

## 7. Key Rotation Procedures

When rotating any API key:

1. Update the new value in `~/.omega/vault/master.env`
2. Run `./scripts/sync-gateway-env.sh --apply` to propagate to all service `.env` files
3. Restart the affected service(s):
   - Gateway: `systemctl restart omega-gateway` (or manual `cargo run`)
   - Brain: restart Node.js process
   - Bridge: restart Python FastAPI process
4. Verify new key works: `curl -s http://localhost:8787/health`
5. Revoke the old key with the provider
6. Log the rotation to `~/NEXUS/ERGON.md` (timestamp + which key rotated, NOT the value)

**Do not:** commit the new key to git. Do not log the new key value. Do not put it in SLACK, Telegram, or any chat platform.

---

## 8. Incident Response

### Category 1: Secret Exposed (in logs, git, chat)

1. **Immediate:** Rotate the exposed key (see §7)
2. **Assess:** Determine scope — was the key publicly accessible? For how long?
3. **Log:** Document to `~/NEXUS/ERGON.md` with `[SECURITY_INCIDENT]` tag
4. **If public exposure:** Notify RY via Telegram immediately; evaluate provider-side usage logs

### Category 2: Identity Contamination Detected

1. **Immediate:** The contaminated response should not be forwarded to users if caught mid-flight
2. **Log:** Record the contamination event with the offending phrase and provider responsible
3. **Remediate:** Review the system prompt injection for the affected provider; update Gateway policy if necessary
4. **Escalate to Council** if the contamination pattern is persistent (Peace Pipe session)

### Category 3: Unauthorized Access Attempt

1. **Log:** 401/403 responses are logged by Gateway with timestamp and source IP
2. **Review:** Check `~/NEXUS/intelligence/log.json` for pattern of access attempts
3. **If persistent:** Update bearer token, notify RY

### Category 4: Runaway Automation

If an agent is executing unsupervised actions beyond the `unsupervised_action_limit` of 5:
1. The Risk Governor triggers — mode drops to Orange (consent required)
2. No further actions until operator confirms
3. Log the sequence to ERGON.md

---

## Changelog

- 1.0.0 (2026-03-13): Initial canonical synthesis from LAW.json, CLAUDE_AUDIT_REPORT.md (2026-03-08 Rust audit), OMEGA_FULL_SYSTEM_SPEC.md, OMEGA_VISION.md.
