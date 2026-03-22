#!/usr/bin/env python3
"""
OmegA One-Block Builder (OBB)
Usage: python obb.py <task> [options]

Generates standardized, reproducible shell scripts for OmegA tasks.
Supported tasks:
  - verify: Generate verification/test script
  - map: Generate repository mapping script
  - serve: Generate documentation server script
  - audit: Generate documentation/link audit script
  - help: Show this help
"""

import argparse
import os
import stat
from pathlib import Path

TEMPLATES = {
    "verify": """#!/bin/bash
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
""",

    "map": """#!/bin/bash
set -e
echo ">> Running OmegA Repo Cartographer..."

# Ensure tool exists
if [ ! -f "tools/repo_cartographer.py" ]; then
    echo "!! Error: tools/repo_cartographer.py not found."
    exit 1
fi

# Run cartographer
echo ">> Generating MANIFEST.md..."
python3 tools/repo_cartographer.py --root . --output MANIFEST.md

echo ">> Mapping Complete. See MANIFEST.md"
""",

    "audit": """#!/bin/bash
set -e
echo ">> Running OmegA Spec Auditor..."

# Ensure tool exists
if [ ! -f "tools/spec_auditor.py" ]; then
    echo "!! Error: tools/spec_auditor.py not found."
    exit 1
fi

# Run auditor
python3 tools/spec_auditor.py --root .

echo ">> Audit Complete: PASS"
""",

    "serve": """#!/bin/bash
set -e
echo ">> Starting OmegA Documentation Server..."

# Simple python server for viewing markdown (rendered if possible, else raw)
echo ">> Serving at http://localhost:8000"
python3 -m http.server 8000
"""
}

def generate_script(task, output_path=None):
    if task not in TEMPLATES:
        print(f"Error: Unknown task '{task}'")
        print(f"Available tasks: {', '.join(TEMPLATES.keys())}")
        return

    content = TEMPLATES[task]
    
    if output_path:
        path = Path(output_path)
        with open(path, "w") as f:
            f.write(content)
        
        # Make executable
        st = os.stat(path)
        os.chmod(path, st.st_mode | stat.S_IEXEC)
        
        print(f"Generated script: {path}")
        print(f"Run with: ./{path}")
    else:
        print(content)

def main():
    parser = argparse.ArgumentParser(description="OmegA One-Block Builder")
    parser.add_argument("task", help="Task to generate script for")
    parser.add_argument("--out", "-o", help="Output file path (optional)")
    
    args = parser.parse_args()
    
    generate_script(args.task, args.out)

if __name__ == "__main__":
    main()
