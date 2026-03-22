#!/bin/bash
set -e
echo ">> Running OmegA Verification Suite..."

# 1. Python Syntax Check
echo ">> Checking Python syntax..."
find . -name "*.py" -not -path "*/.*" -exec python3 -m py_compile {} +

# 2. Knowledge Graph Integrity
if [ -f "omega_equation_knowledge_graph.json" ]; then
    echo ">> Verifying Knowledge Graph..."
    python3 omega_kg_explorer.py --list-nodes > /dev/null
else
    echo "!! Warning: Knowledge Graph not found."
fi

echo ">> Verification Complete: PASS"
