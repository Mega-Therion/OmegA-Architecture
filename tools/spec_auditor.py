#!/usr/bin/env python3
import os
import re
import argparse
import sys
from pathlib import Path
from urllib.parse import unquote

LINK_PATTERN = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')
SPEC_PATTERN = re.compile(r'@OMEGA_SPEC:\s*([A-Z0-9_]+)\s*\|\s*(.*)')

def scan_files(root_path):
    specs = {}
    broken_links = []
    
    # Debug print to stderr to ensure it appears
    print(f"DEBUG: Scanning in {root_path}...", file=sys.stderr)
    
    for root, dirs, files in os.walk(root_path):
        if ".git" in dirs:
            dirs.remove(".git")
            
        for file in files:
            path = Path(root) / file
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
                for match in SPEC_PATTERN.finditer(content):
                    spec_id, desc = match.groups()
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
    parser.add_argument("--root", default=".")
    args = parser.parse_args()
    root = Path(args.root).resolve()
    specs, broken_links = scan_files(root)
    print(f"\n--- Audit Results ---")
    print(f"Specs Identified: {len(specs)}")
    for sid, info in specs.items():
        print(f"  [{sid}] {info['desc']} (Found in {len(info['locations'])} file(s))")
    if broken_links:
        for e in broken_links: print(f"  - {e}")
