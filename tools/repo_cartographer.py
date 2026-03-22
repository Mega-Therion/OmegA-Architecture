#!/usr/bin/env python3
"""
OmegA Repo Cartographer
Usage: python repo_cartographer.py [options]

Generates a living manifest of the OmegA codebase.
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", "dist", "build", ".venv", ".mypy_cache"
}
IGNORE_FILES = {
    ".DS_Store", "package-lock.json", "yarn.lock"
}
EXTENSIONS = {
    ".py": "Python",
    ".md": "Markdown",
    ".json": "JSON",
    ".sh": "Shell",
    ".rs": "Rust",
    ".toml": "TOML",
    ".yml": "YAML",
    ".yaml": "YAML",
    ".js": "JavaScript",
    ".ts": "TypeScript",
    ".txt": "Text"
}

def get_file_type(path):
    return EXTENSIONS.get(path.suffix, "Other")

def get_description(path):
    """Attempt to read the first line or docstring."""
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            first_line = f.readline().strip()
            if first_line.startswith("#!"):
                # Skip shebang
                first_line = f.readline().strip()
            
            if path.suffix == ".py":
                # Check for module docstring
                content = path.read_text(encoding="utf-8", errors="ignore")
                if '"""' in content[:100]: # naive check
                    start = content.find('"""') + 3
                    end = content.find('"""', start)
                    if end != -1:
                        return content[start:end].strip().split('\n')[0]
            
            if first_line.startswith("# ") or first_line.startswith("// "):
                return first_line.lstrip("#/ ").strip()
            if first_line.startswith('"""'):
                 return first_line.strip('"""').strip()
            return first_line[:80] + "..." if len(first_line) > 80 else first_line
    except Exception:
        return ""

def scan_repo(root_path):
    manifest = {
        "generated_at": datetime.now().isoformat(),
        "root": str(root_path),
        "files": [],
        "stats": {k: 0 for k in EXTENSIONS.values()}
    }
    manifest["stats"]["Other"] = 0
    manifest["total_files"] = 0
    manifest["total_size_bytes"] = 0

    for root, dirs, files in os.walk(root_path):
        # Filter directories in-place
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file in IGNORE_FILES:
                continue
                
            path = Path(root) / file
            rel_path = path.relative_to(root_path)
            
            file_type = get_file_type(path)
            size = path.stat().st_size
            desc = get_description(path)
            
            entry = {
                "path": str(rel_path),
                "type": file_type,
                "size": size,
                "description": desc,
                "modified": datetime.fromtimestamp(path.stat().st_mtime).isoformat()
            }
            
            manifest["files"].append(entry)
            manifest["stats"][file_type] += 1
            manifest["total_files"] += 1
            manifest["total_size_bytes"] += size

    return manifest

def generate_markdown(manifest):
    lines = [
        "# OmegA Repository Manifest",
        f"\n**Generated:** {manifest['generated_at']}",
        f"**Total Files:** {manifest['total_files']}",
        f"**Total Size:** {manifest['total_size_bytes'] / 1024:.2f} KB",
        "\n## Language Distribution",
        "| Language | Files |",
        "|----------|-------|"
    ]
    
    for lang, count in sorted(manifest["stats"].items(), key=lambda x: x[1], reverse=True):
        if count > 0:
            lines.append(f"| {lang} | {count} |")
            
    lines.append("\n## File Inventory")
    lines.append("| Path | Type | Size | Description |")
    lines.append("|------|------|------|-------------|")
    
    for f in sorted(manifest["files"], key=lambda x: x["path"]):
        lines.append(f"| `{f['path']}` | {f['type']} | {f['size']} | {f['description']} |")
        
    return "\n".join(lines)

def main():
    parser = argparse.ArgumentParser(description="OmegA Repo Cartographer")
    parser.add_argument("--root", default=".", help="Root directory to scan")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format")
    parser.add_argument("--output", help="Output file path (default: stdout)")
    
    args = parser.parse_args()
    
    root_path = Path(args.root).resolve()
    manifest = scan_repo(root_path)
    
    if args.format == "json":
        output = json.dumps(manifest, indent=2)
    else:
        output = generate_markdown(manifest)
        
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output)
        print(f"Manifest written to {args.output}")
    else:
        print(output)

if __name__ == "__main__":
    main()
