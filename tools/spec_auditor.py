#!/usr/bin/env python3
import argparse
import os
import re
import sys
from pathlib import Path
from urllib.parse import unquote

LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
SPEC_PATTERN = re.compile(r'@OMEGA_SPEC:\s*([A-Z0-9_]+)\s*\|\s*(.*)')
ALLOWED_SUFFIXES = {".md", ".py", ".rs"}
IGNORED_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "output",
    "target",
    "vendor",
}

def scan_files(root_path):
    specs = {}
    broken_links = []

    if not root_path.exists():
        return specs, broken_links

    for root, dirs, files in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]

        for file in files:
            path = Path(root) / file
            if path.suffix not in ALLOWED_SUFFIXES:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for match in SPEC_PATTERN.finditer(content):
                    spec_id, desc = match.groups()
                    desc = re.sub(r"\s*-->\s*$", "", desc).strip()
                    if spec_id not in specs:
                        specs[spec_id] = {"desc": desc, "locations": []}
                    specs[spec_id]["locations"].append(str(path))
                if file.endswith(".md"):
                    for match in LINK_PATTERN.finditer(content):
                        _, link = match.groups()
                        if not link.startswith(("http", "mailto:")):
                            if "#" in link: link = link.split("#")[0]
                            if link and not (path.parent / unquote(link)).resolve().exists():
                                broken_links.append(f"{path}: Broken link to '{link}'")
            except Exception:
                continue
    return specs, broken_links

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--root",
        action="append",
        dest="roots",
        help="Root directory to scan. Repeat for multiple roots.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    roots = args.roots or ["papers", "specs"]

    specs = {}
    broken_links = []
    for rel_root in roots:
        root = (repo_root / rel_root).resolve() if not Path(rel_root).is_absolute() else Path(rel_root).resolve()
        part_specs, part_broken = scan_files(root)
        for spec_id, info in part_specs.items():
            if spec_id not in specs:
                specs[spec_id] = {"desc": info["desc"], "locations": []}
            specs[spec_id]["locations"].extend(info["locations"])
        broken_links.extend(part_broken)

    print(f"\n--- Audit Results ---")
    print(f"Specs Identified: {len(specs)}")
    for sid, info in specs.items():
        print(f"  [{sid}] {info['desc']} (Found in {len(info['locations'])} file(s))")
    if broken_links:
        for e in broken_links: print(f"  - {e}")
        sys.exit(1)
    if not specs:
        print("  - No @OMEGA_SPEC tags found in the requested roots.", file=sys.stderr)
        sys.exit(1)
    sys.exit(0)
