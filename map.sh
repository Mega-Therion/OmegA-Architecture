#!/bin/bash
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
