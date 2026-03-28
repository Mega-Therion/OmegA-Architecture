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

echo ">> Verification Complete: PASS"
