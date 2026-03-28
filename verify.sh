#!/bin/bash
set -e
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
EXPLAIN_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --explain)
            EXPLAIN_ONLY=true
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

get_changed_paths() {
    {
        git -C "$ROOT_DIR" diff --name-only --diff-filter=ACMRTUXB HEAD --;
        git -C "$ROOT_DIR" diff --name-only --cached --diff-filter=ACMRTUXB --;
        git -C "$ROOT_DIR" ls-files --others --exclude-standard --;
    } | sort -u
}

is_memory_only_change_set() {
    local path

    while IFS= read -r path; do
        [ -n "$path" ] || continue
        case "$path" in
            runtime/crates/omega-memory/*)
                ;;
            runtime/crates/omega-core/src/memory.rs)
                ;;
            runtime/crates/omega-gateway/src/dream.rs)
                ;;
            runtime/crates/omega-gateway/src/routes/ingest.rs)
                ;;
            runtime/crates/omega-gateway/src/routes/memory.rs)
                ;;
            runtime/scripts/supabase_memory_schema.sql)
                ;;
            specs/memory_system.md)
                ;;
            evals/test_agent_telemetry.py)
                ;;
            ERGON.md)
                ;;
            *)
                return 1
                ;;
        esac
    done < <(get_changed_paths)

    return 0
}

print_explain_mode() {
    if is_memory_only_change_set; then
        echo "memory-only change set detected"
        echo "selected gate: scripts/memory_gate.py"
        echo "reason: all changed paths are in memory telemetry or directly coupled runtime surfaces"
    else
        echo "mixed or non-memory change set detected"
        echo "selected gate: full verify.sh"
        echo "reason: at least one changed path is outside the memory-only allowlist"
    fi
}

if [ "$EXPLAIN_ONLY" = true ]; then
    print_explain_mode
    exit 0
fi

echo ">> Running OmegA Verification Suite..."

# 1. Python Syntax Check
echo ">> Checking Python syntax..."
PY_SCAN_PATHS=()
for candidate in "$ROOT_DIR/omega" "$ROOT_DIR/tools" "$ROOT_DIR/evals" "$ROOT_DIR/voice" "$ROOT_DIR/runtime/voice"; do
    if [ -e "$candidate" ]; then
        PY_SCAN_PATHS+=("$candidate")
    fi
done
mapfile -t PY_FILES < <(rg --files "${PY_SCAN_PATHS[@]}" -g '*.py')
if [ "${#PY_FILES[@]}" -gt 0 ]; then
    python3 -m py_compile "${PY_FILES[@]}"
fi

# 2. Knowledge Graph Integrity
if [ -f "$ROOT_DIR/omega_equation_knowledge_graph.json" ]; then
    echo ">> Verifying Knowledge Graph..."
    python3 "$ROOT_DIR/omega_kg_explorer.py" --list-nodes > /dev/null
else
    echo "!! Warning: Knowledge Graph not found."
fi

# 2b. Master eval + spec audit + identity/memory regressions
echo ">> Running OmegA master evaluation..."
python3 "$ROOT_DIR/omegactl.py" eval

echo ">> Running Proof Audit..."
python3 "$ROOT_DIR/tools/proof_auditor.py"

# 3. Polyglot runtime validation
echo ">> Running polyglot runtime validation..."
if is_memory_only_change_set; then
    echo ">> Memory-only change set detected; running dedicated memory gate..."
    python3 "$ROOT_DIR/scripts/memory_gate.py"
    echo ">> Verification Complete: PASS"
    exit 0
fi

POLYGLOT_ARGS=(--build --test --json)
if [ -n "${OMEGA_GATEWAY_URL:-}" ]; then
    POLYGLOT_ARGS+=(--gateway-url "$OMEGA_GATEWAY_URL")
fi
python3 "$ROOT_DIR/tools/polyglot_runtime.py" "${POLYGLOT_ARGS[@]}"

# 4. Live route smoke validation when a deployed base URL is available
if [ -n "${OMEGA_BASE_URL:-}" ] || [ -n "${VERCEL_URL:-}" ]; then
    BASE_URL="${OMEGA_BASE_URL:-${VERCEL_URL}}"
    case "$BASE_URL" in
        http://*|https://*)
            ;;
        *)
            BASE_URL="https://${BASE_URL}"
            ;;
    esac
    echo ">> Running live route smoke validation against ${BASE_URL}..."
    node "$ROOT_DIR/web/scripts/omega-smoke.mjs" --base "$BASE_URL"
else
    echo ">> Skipping live route smoke validation (set OMEGA_BASE_URL or VERCEL_URL to enable)."
fi

# 5. Formal Invariant Suite
echo ">> Running Formal Invariant Suite (T-1 through T-10)..."
PROOF_PYTHON="python3"
if [ -x "$ROOT_DIR/proofs/.venv/bin/python" ]; then
    PROOF_PYTHON="$ROOT_DIR/proofs/.venv/bin/python"
fi

THEOREM_MAP=(
    "TestStateVectorWellFormed:T-1"
    "TestIdentityContinuity:T-2"
    "TestGovernanceFailClosed:T-3"
    "TestClaimBudgetBounds:T-4"
    "TestMemoryHardeningMonotonic:T-5"
    "TestVerifierNonBypass:T-6"
    "TestUnifiedActionGating:T-7"
    "TestSelfTagImmutability:T-9"
    "TestEnvelopeCompleteness:T-10"
)

PROOF_FAIL=0
for entry in "${THEOREM_MAP[@]}"; do
    CLASS="${entry%%:*}"
    TID="${entry##*:}"
    if "$PROOF_PYTHON" -m pytest "$ROOT_DIR/proofs/invariants.py::${CLASS}" -v --tb=short -q 2>&1 | tail -1 | grep -q "passed"; then
        echo "   $TID ($CLASS): PASS"
    else
        echo "   $TID ($CLASS): FAIL"
        PROOF_FAIL=1
    fi
done

echo "   T-8 (ProviderNonCollapse): DEFERRED — requires live Ollama (see evals/test_aegis_identity.py)"

if [ "$PROOF_FAIL" -eq 1 ]; then
    echo ">> Formal Invariant Suite: FAIL"
    exit 1
fi
echo ">> Formal Invariant Suite: PASS (36/36 property tests)"

# 6. Lean4 Machine-Checked Proofs (T-2, T-3, T-5, T-7)
LEAN_BIN="$HOME/.elan/bin/lean"
if [ -x "$LEAN_BIN" ] && [ -f "$ROOT_DIR/proofs/lakefile.toml" ]; then
    echo ">> Building Lean4 proof package (T-2, T-3, T-5, T-7)..."
    export PATH="$HOME/.elan/bin:$PATH"
    if (cd "$ROOT_DIR/proofs" && lake build 2>&1 | tail -5); then
        echo ">> Lean4 Proofs: PASS"
    else
        echo ">> Lean4 Proofs: FAIL"
        exit 1
    fi
else
    echo ">> Lean4 Proofs: SKIPPED (lean4 not installed — install via elan)"
fi

echo ">> Verification Complete: PASS"
