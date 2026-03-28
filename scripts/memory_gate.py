#!/usr/bin/env python3
"""Run the dedicated OmegA memory-only release gate.

This gate is intentionally narrower than ``verify.sh``:
- it only exercises the ``omega-memory`` Rust crate
- it includes both unit and integration tests
- it is the fast path for retrieval telemetry regressions
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    runtime_dir = repo_root / "runtime"

    print(">> Running OmegA memory gate...", flush=True)
    print(">> Running cargo test -p omega-memory ...", flush=True)

    result = subprocess.run(
        ["cargo", "test", "-p", "omega-memory"],
        cwd=runtime_dir,
        check=False,
    )
    if result.returncode != 0:
        print(">> Memory gate: FAIL", file=sys.stderr, flush=True)
        return result.returncode

    print(">> Memory gate: PASS", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
