# Alye — Blind Tester Onboarding

This document gets you running in under 10 minutes. No prior context about OmegA is assumed.

---

## Prerequisites

Install these before you start:

| Tool | Version | Why |
|---|---|---|
| Python | 3.12+ | All test suites |
| Git | any | Clone the repo |
| ripgrep (`rg`) | any | Required by verify.sh |
| Ollama (optional) | any | Live integration tests only |

Install ripgrep: `sudo apt install ripgrep` (Debian/Ubuntu) or `brew install ripgrep` (macOS).

---

## One-Command Setup

```bash
git clone https://github.com/Mega-Therion/OmegA-Architecture.git && cd OmegA-Architecture
```

No pip install required for the conformance suite. The `omega/` package and test files run with Python stdlib + whatever is already importable.

---

## Test Sequence

Run these in order. Each step is independent — a failure at step 3 does not block steps 4 or 5.

### Step 1 — Conformance suite (the core gate)

```bash
python3 omegactl.py eval
```

What to expect: `59/59 PASS`. Exit code 0.
Time: under 30 seconds, no network.

### Step 2 — Spec auditor

```bash
python3 tools/spec_auditor.py
```

What to expect: 20 `@OMEGA_SPEC` tags found, no broken references. Exit code 0.

### Step 3 — Knowledge graph check

```bash
python3 omega_kg_explorer.py --list-nodes > /dev/null && echo "KG OK"
```

What to expect: `KG OK` printed. Exit code 0.

### Step 4 — AEGIS identity invariant

```bash
python3 evals/test_aegis_identity.py
```

What to expect: `1/1 PASS`. Tests that the governance layer enforces identity even without an identity kernel loaded.

### Step 5 — Live integration (skip if no Ollama)

```bash
python3 evals/test_live_ollama.py --model llama3.2:3b
```

What to expect: `14/15 PASS`. The one known failure is documented. If you see a different failure, that is a regression.

### Step 6 — Full release gate

```bash
bash verify.sh
```

What to expect: `Verification Complete: PASS`. This runs Python syntax checks, knowledge graph validation, and the polyglot runtime validation.

---

## What to Report Back

After running, send back:

1. **Step 1 result:** exact pass/fail count (e.g., `59/59 PASS` or `57/59 — 2 failures`)
2. **Step 2 result:** spec count and any broken references
3. **Step 4 result:** `1/1 PASS` or failure message
4. **Step 5 result (if run):** pass count and which test failed, if any
5. **Step 6 result:** `PASS` or the first error line
6. **Your environment:** OS, Python version, whether Ollama was available
7. **Any blockers** you hit that prevented a step from running at all

You do not need to understand the architecture to run these tests. If a step fails, copy the full terminal output — the error messages are the evidence.

---

## What You Are NOT Being Asked to Judge

- Whether OmegA is conscious or "really" intelligent
- Whether the architecture is novel compared to other published work
- Whether the production deployment is stable

You are being asked to verify: **does the test suite pass on a clean clone of this repo?**

---

## Read Next (if you want context)

- `publication/EXTERNAL_VERIFICATION.md` — what OmegA claims and where all evidence lives
- `publication/SELF_DESCRIPTION_CONTRACT.md` — what OmegA says it is, in its own terms
- `publication/VERIFICATION_RUBRIC.md` — structured pass/fail criteria for each claim
- `publication/CLAIM_LEDGER.md` — which claims are proven vs. aspirational
