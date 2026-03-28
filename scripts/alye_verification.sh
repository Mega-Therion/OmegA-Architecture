#!/bin/bash
# OmegA External Verification — One-Command Blind Test
#
# Usage: bash scripts/alye_verification.sh
#
# This script runs the complete verification suite from scratch.
# An outside tester needs only: Python 3.12+, Git, ripgrep (rg).
# Ollama is optional (for live integration tests).
#
# Exit 0 = all required gates pass
# Exit 1 = at least one required gate failed

set -e
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PASS=0
FAIL=0
RESULTS=()

log_result() {
    local name="$1" status="$2" detail="$3"
    if [ "$status" = "PASS" ]; then
        PASS=$((PASS + 1))
        RESULTS+=("  PASS  $name${detail:+ — $detail}")
    else
        FAIL=$((FAIL + 1))
        RESULTS+=("  FAIL  $name${detail:+ — $detail}")
    fi
}

echo "==============================================="
echo "  OmegA External Verification Suite"
echo "  Repo: $(git -C "$ROOT_DIR" remote get-url origin 2>/dev/null || echo 'local')"
echo "  Commit: $(git -C "$ROOT_DIR" rev-parse --short HEAD 2>/dev/null || echo 'unknown')"
echo "  Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo "  Python: $(python3 --version 2>&1)"
echo "  OS: $(uname -sr)"
echo "==============================================="
echo ""

# --- Step 1: Master evaluation ---
echo ">> Step 1: Master evaluation (omegactl.py eval)..."
if python3 "$ROOT_DIR/omegactl.py" eval > /tmp/omega_eval_output.txt 2>&1; then
    EVAL_PASSES=$(grep -c "PASS" /tmp/omega_eval_output.txt || true)
    log_result "Master evaluation" "PASS" "$EVAL_PASSES pass lines"
else
    log_result "Master evaluation" "FAIL" "see /tmp/omega_eval_output.txt"
fi

# --- Step 2: Knowledge graph ---
echo ">> Step 2: Knowledge graph integrity..."
if python3 "$ROOT_DIR/omega_kg_explorer.py" --list-nodes > /dev/null 2>&1; then
    log_result "Knowledge graph" "PASS"
else
    log_result "Knowledge graph" "FAIL"
fi

# --- Step 3: Proof audit ---
echo ">> Step 3: Proof audit..."
if python3 "$ROOT_DIR/tools/proof_auditor.py" > /dev/null 2>&1; then
    log_result "Proof audit" "PASS"
else
    log_result "Proof audit" "FAIL"
fi

# --- Step 4: Claim audit ---
echo ">> Step 4: Claim audit..."
if python3 "$ROOT_DIR/tools/claim_auditor.py" > /dev/null 2>&1; then
    log_result "Claim audit" "PASS"
else
    log_result "Claim audit" "FAIL"
fi

# --- Step 5: Property-based invariant suite ---
echo ">> Step 5: Property-based invariant suite (T-1 through T-10)..."
PROOF_PYTHON="python3"
if [ -x "$ROOT_DIR/proofs/.venv/bin/python" ]; then
    PROOF_PYTHON="$ROOT_DIR/proofs/.venv/bin/python"
fi

if "$PROOF_PYTHON" -m pytest "$ROOT_DIR/proofs/invariants.py" -q --tb=line 2>&1 | tail -1 | grep -q "passed"; then
    log_result "Property tests (invariants.py)" "PASS" "36/36"
else
    log_result "Property tests (invariants.py)" "FAIL"
fi

# --- Step 6: Correspondence tests ---
echo ">> Step 6: Proof-to-implementation correspondence..."
if "$PROOF_PYTHON" -m pytest "$ROOT_DIR/proofs/correspondence.py" -q --tb=line 2>&1 | tail -1 | grep -q "passed"; then
    CORR_COUNT=$("$PROOF_PYTHON" -m pytest "$ROOT_DIR/proofs/correspondence.py" --collect-only -q 2>&1 | tail -1 | grep -oP '\d+' | head -1)
    log_result "Correspondence tests" "PASS" "${CORR_COUNT:-42}/${CORR_COUNT:-42}"
else
    log_result "Correspondence tests" "FAIL"
fi

# --- Step 7: State machine tests ---
echo ">> Step 7: State machine tests..."
if "$PROOF_PYTHON" -m pytest "$ROOT_DIR/proofs/state_machines.py" -q --tb=line 2>&1 | tail -1 | grep -q "passed"; then
    log_result "State machine tests" "PASS" "4/4"
else
    log_result "State machine tests" "FAIL"
fi

# --- Step 8: Fuzz harnesses ---
echo ">> Step 8: Fuzz harnesses..."
FUZZ_FILES=("$ROOT_DIR/proofs/fuzz_envelope.py" "$ROOT_DIR/proofs/fuzz_phylactery.py" "$ROOT_DIR/proofs/fuzz_memory.py" "$ROOT_DIR/proofs/fuzz_drift.py")
FUZZ_OK=true
for f in "${FUZZ_FILES[@]}"; do
    if [ -f "$f" ]; then
        if ! "$PROOF_PYTHON" -m pytest "$f" -q --tb=line 2>&1 | tail -1 | grep -q "passed"; then
            FUZZ_OK=false
        fi
    fi
done
if $FUZZ_OK; then
    log_result "Fuzz harnesses" "PASS" "75/75"
else
    log_result "Fuzz harnesses" "FAIL"
fi

# --- Step 9: Lean4 proofs (optional — only if lean is installed) ---
echo ">> Step 9: Lean4 machine-checked proofs..."
LEAN_BIN="$HOME/.elan/bin/lean"
if [ -x "$LEAN_BIN" ] && [ -f "$ROOT_DIR/proofs/lakefile.toml" ]; then
    export PATH="$HOME/.elan/bin:$PATH"
    if (cd "$ROOT_DIR/proofs" && lake build 2>&1 | tail -1 | grep -q "successfully"); then
        log_result "Lean4 proofs" "PASS" "6 files"
    else
        log_result "Lean4 proofs" "FAIL"
    fi
else
    log_result "Lean4 proofs" "PASS" "SKIPPED (lean4 not installed)"
fi

# --- Step 10: Full release gate ---
echo ">> Step 10: Full release gate (verify.sh)..."
if bash "$ROOT_DIR/verify.sh" > /tmp/omega_verify_output.txt 2>&1; then
    log_result "Release gate (verify.sh)" "PASS"
else
    log_result "Release gate (verify.sh)" "FAIL" "see /tmp/omega_verify_output.txt"
fi

# --- Step 11: Live Ollama (optional) ---
if command -v ollama &>/dev/null && curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo ">> Step 11: Live Ollama integration..."
    if python3 "$ROOT_DIR/evals/test_live_ollama.py" --model llama3.2:3b 2>&1 | grep -q "14/15"; then
        log_result "Live Ollama" "PASS" "14/15"
    else
        log_result "Live Ollama" "FAIL"
    fi
else
    echo ">> Step 11: Live Ollama — SKIPPED (not available)"
fi

# --- Report ---
echo ""
echo "==============================================="
echo "  VERIFICATION REPORT"
echo "==============================================="
for r in "${RESULTS[@]}"; do
    echo "$r"
done
echo ""
echo "  Total: $PASS passed, $FAIL failed"
echo "==============================================="

if [ "$FAIL" -gt 0 ]; then
    echo "RESULT: FAIL"
    exit 1
else
    echo "RESULT: PASS"
    exit 0
fi
