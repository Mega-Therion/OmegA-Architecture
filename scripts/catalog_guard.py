#!/usr/bin/env python3
"""Validate that the catalog registry matches the repo tree."""

from __future__ import annotations

import sys
from pathlib import Path

from catalog_registry import validate_registry


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]

    errors = validate_registry(repo_root)
    if errors:
        print("Catalog guard failed:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1

    print("Catalog guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
