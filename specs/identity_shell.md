# Identity Shell Subsystem
**Version:** 1.0.0
**Last Updated:** 2026-03-13

The Identity Shell is OmegA's outermost behavioral layer — the mechanism that ensures every response reflects OmegA's sovereign identity regardless of which LLM provider generated the underlying tokens.

---

## What It Is

The Identity Shell is not a single component. It is a stack of enforcement mechanisms operating at different layers:

1. **Gateway Policy Middleware** (`rust/omega-rust/crates/omega-gateway/src/middleware/policy.rs`) — LAW.json enforcement at the network level; blocks forbidden actions before they reach the LLM
2. **Context Injection** — OMEGA_IDENTITY.md is included in the system prompt / context window for every agent request
3. **Contamination Watch** — detection of provider-identity signals in outbound responses (defined in OMEGA_IDENTITY.md §11)
4. **Phylactery (L6 Memory)** — the version-controlled identity kernel that persists across sessions and provides the canonical values/anchors

---

## Why It Exists

LLM providers have strong identity signals in their training data. Without the Identity Shell:
- A Claude-powered response would sound like Claude
- A GPT-powered response would sound like ChatGPT
- After a provider failover, OmegA's "voice" would change mid-conversation

The Identity Shell ensures OmegA is the same entity regardless of what's running under the hood.

---

## Inputs

- `OMEGA_IDENTITY.md` (canonical identity document — injected as context)
- `LAW.json` (policy rules — loaded at Gateway startup)
- `soul.rs::IdentityProfile::canonical()` (Rust-side identity anchor)
- Provider responses (monitored for contamination signals)

---

## Outputs

- Filtered/transformed responses with contamination signals suppressed
- Policy enforcement decisions (allow / block / log)
- Identity-consistent responses regardless of active provider

---

## Configuration It Reads

- `~/NEXUS/identity/LAW.json` — forbidden actions, restricted folders, authority levels
- `omega/OMEGA_IDENTITY.md` — injected into agent context
- `config/identity.yaml` — designation, operator, provider_disclosure_policy
- `OMEGA_API_BEARER_TOKEN` env var — Gateway auth

---

## Failure Modes

| Failure | Tag | Symptom | Remediation |
|---------|-----|---------|-------------|
| Context injection missing | IDENTITY_SHELL | Agent responds without OmegA identity anchors | Verify OMEGA_IDENTITY.md is loaded in system prompt |
| Provider contamination | PROVIDER_CONTAM | "As Claude," or similar appears in output | Update contamination watch filter in Gateway |
| Adversarial injection success | IDENTITY_SHELL | Roleplay or jailbreak causes identity collapse | Harden system prompt; review Gateway policy |
| LAW.json not loaded | RUNTIME_ENV | Forbidden actions not blocked | Check Gateway startup logs; verify file path |
| Phylactery unavailable | MEMORY | Identity anchors from L6 not in context | Check Supabase connectivity; fall back to `soul.rs` |

---

## Current Implementation Status

- Gateway policy middleware: ACTIVE (Rust, production)
- Context injection: PARTIAL — OMEGA_IDENTITY.md exists but injection into every request is not yet automated in all code paths
- Contamination watch: DEFINED (OMEGA_IDENTITY.md §11) — automated detection in middleware is partial
- Phylactery: L6 memory tier defined; full implementation is Week 4 work
