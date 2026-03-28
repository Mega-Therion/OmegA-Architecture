#!/usr/bin/env python3
"""Generate or validate the OmegA catalog registry from the repository tree."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from catalog_registry import build_registry, validate_registry, write_registry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate the registry without writing changes.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the generated registry to catalog/registry.json.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]

    if args.check and args.write:
        print("Choose only one of --check or --write.", file=sys.stderr)
        return 2

    if args.write:
        generated = write_registry(repo_root)
        print(
            f"Wrote catalog/registry.json with {len(generated['directories'])} top-level entries.",
        )
        return 0

    errors = validate_registry(repo_root)
    if errors:
        print("Catalog registry needs attention:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        if args.check:
            return 1
        print("Run `python3 scripts/catalog_sync.py --write` to regenerate it.", file=sys.stderr)
        return 1

    generated = build_registry(repo_root)
    print(f"Catalog registry is synchronized ({len(generated['directories'])} entries).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
