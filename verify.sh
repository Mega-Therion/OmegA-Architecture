#!/bin/bash
set -e
echo ">> Running OmegA Verification Suite..."
ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 1. Python Syntax Check
echo ">> Checking Python syntax..."
mapfile -t PY_FILES < <(rg --files "$ROOT_DIR/omega" "$ROOT_DIR/tools" "$ROOT_DIR/evals" "$ROOT_DIR/voice" "$ROOT_DIR/runtime/voice" -g '*.py')
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

# 3. Polyglot runtime validation
echo ">> Running polyglot runtime validation..."
python3 "$ROOT_DIR/tools/polyglot_runtime.py" --build --test --json

echo ">> Verification Complete: PASS"
