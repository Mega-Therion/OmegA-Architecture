# Alye — Blind Tester Onboarding

This is the blind path for an outside tester. No prior context about OmegA is assumed.

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

No pip install is required for the blind verification path. The `omega/` package and test files run with Python stdlib + whatever is already importable.

---

## Test Sequence

Run these in order. Each step is independent.

### Step 1 — Master eval (the core blind gate)

```bash
python3 omegactl.py eval
```

What to expect:
- `OMEGA_SPEC_AUDITOR: PASS`
- `AEGIS_IDENTITY_ENFORCEMENT: PASS`
- `OMEGA_CONFORMANCE_SUITE: PASS`
- `OMEGA_CROSS_SESSION_IDENTITY: PASS`
- `OMEGA_MEMORY_UTILITY_GROWTH: PASS`

Exit code 0.

### Step 2 — Knowledge graph check

```bash
python3 omega_kg_explorer.py --list-nodes > /dev/null && echo "KG OK"
```

What to expect: `KG OK` printed. Exit code 0.

### Step 3 — Live integration (optional if Ollama is available)

```bash
python3 evals/test_live_ollama.py --model llama3.2:3b
```

What to expect: `14/15 PASS`. The one known failure is documented.

### Step 4 — Full release gate

```bash
bash verify.sh
```

What to expect: `Verification Complete: PASS`. This runs Python syntax checks, knowledge graph validation, and the polyglot runtime validation.

---

## What to Report Back

After running, send back:

1. **Step 1 result:** the five PASS lines from `python3 omegactl.py eval`
2. **Step 2 result:** `KG OK` or the first error line
3. **Step 3 result (if run):** pass count and which test failed, if any
4. **Step 4 result:** `PASS` or the first error line
5. **Your environment:** OS, Python version, whether Ollama was available
6. **Any blockers** you hit that prevented a step from running at all

You do not need to understand the architecture to run these tests. If a step fails, copy the full terminal output — the error messages are the evidence.

---

## What You Are NOT Being Asked to Judge

- Whether OmegA is conscious or "really" intelligent
- Whether the architecture is novel compared to other published work
- Whether the production deployment is stable

You are being asked to verify: **does the blind verification path pass on a clean clone of this repo?**

---

## Read Next (if you want context)

- `publication/EXTERNAL_VERIFICATION.md` — what OmegA claims and where all evidence lives
- `publication/SELF_DESCRIPTION_CONTRACT.md` — what OmegA says it is, in its own terms
- `publication/VERIFICATION_RUBRIC.md` — structured pass/fail criteria for each claim
- `publication/CLAIM_LEDGER.md` — which claims are proven vs. aspirational
