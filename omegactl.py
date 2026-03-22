#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path

def run(cmd):
    try:
        subprocess.run(cmd, check=True)
    except Exception as e:
        print(f"Error running {' '.join(cmd)}: {e}")

def main():
    if len(sys.argv) < 2:
        print("Usage: omegactl <audit|eval|map|build>")
        return

    cmd = sys.argv[1]
    if cmd == "audit":
        run(["python3", "tools/spec_auditor.py"])
    elif cmd == "eval":
        run(["python3", "tools/master_eval.py"])
    elif cmd == "map":
        run(["python3", "tools/repo_cartographer.py", "--output", "MANIFEST.md"])
    elif cmd == "build":
        run(["python3", "tools/obb.py", "verify", "--out", "verify.sh"])
    else:
        print(f"Unknown command: {cmd}")

if __name__ == "__main__":
    main()
