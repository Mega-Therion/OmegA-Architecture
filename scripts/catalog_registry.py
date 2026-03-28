#!/usr/bin/env python3
"""Shared catalog registry helpers for OmegA."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any


DEFAULT_IGNORE_DIRECTORIES = [
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
    ".next",
    "dist",
]


DEFAULT_POLICY = {
    "oneCanonicalHomePerArtifact": True,
    "registerBeforeCreate": True,
    "scratchBelongsInInbox": True,
    "generatedOutputsStayIsolated": True,
}


def repo_root_for(script_path: Path) -> Path:
    return script_path.resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def discover_top_level_directories(repo_root: Path, ignore: set[str] | None = None) -> list[str]:
    ignored = set(DEFAULT_IGNORE_DIRECTORIES if ignore is None else ignore)
    return sorted(
        item.name
        for item in repo_root.iterdir()
        if item.is_dir() and item.name not in ignored
    )


def load_registry(path: Path) -> dict[str, Any]:
    if path.exists():
        return load_json(path)
    return {
        "version": 1,
        "root": str(path.parents[1]),
        "policy": copy.deepcopy(DEFAULT_POLICY),
        "ignoreTopLevelDirectories": list(DEFAULT_IGNORE_DIRECTORIES),
        "directories": [],
    }


def _default_directory_entry(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "path": f"{name}/",
        "category": "unclassified",
        "purpose": "Discovered by the catalog generator and awaiting canonical classification.",
        "owner": "unassigned",
        "read_first": False,
        "allowed_contents": [],
        "forbidden_contents": [
            "source canon",
            "unaudited runtime",
            "secrets",
        ],
        "validation": "catalog review required",
        "approved": False,
    }


def build_registry(repo_root: Path, existing_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    registry_path = repo_root / "catalog" / "registry.json"
    current = existing_registry if existing_registry is not None else load_registry(registry_path)

    actual_dirs = discover_top_level_directories(
        repo_root,
        set(current.get("ignoreTopLevelDirectories", DEFAULT_IGNORE_DIRECTORIES)),
    )

    existing_entries = {
        entry["name"]: copy.deepcopy(entry)
        for entry in current.get("directories", [])
        if isinstance(entry, dict) and "name" in entry
    }

    ordered_names = [entry["name"] for entry in current.get("directories", []) if entry.get("name") in actual_dirs]
    new_names = sorted(name for name in actual_dirs if name not in existing_entries)

    directories: list[dict[str, Any]] = []
    for name in ordered_names + new_names:
        entry = existing_entries.get(name, _default_directory_entry(name))
        entry["name"] = name
        entry["path"] = f"{name}/"
        entry.setdefault("approved", True)
        if name in existing_entries:
            entry["approved"] = True
        directories.append(entry)

    return {
        "version": int(current.get("version", 1)),
        "root": str(repo_root),
        "policy": copy.deepcopy(current.get("policy", DEFAULT_POLICY)),
        "ignoreTopLevelDirectories": list(current.get("ignoreTopLevelDirectories", DEFAULT_IGNORE_DIRECTORIES)),
        "directories": directories,
    }


def write_registry(repo_root: Path, existing_registry: dict[str, Any] | None = None) -> dict[str, Any]:
    generated = build_registry(repo_root, existing_registry=existing_registry)
    write_json(repo_root / "catalog" / "registry.json", generated)
    return generated


def validate_registry(repo_root: Path, existing_registry: dict[str, Any] | None = None) -> list[str]:
    current = existing_registry if existing_registry is not None else load_registry(repo_root / "catalog" / "registry.json")
    generated = build_registry(repo_root, existing_registry=current)

    errors: list[str] = []
    if current != generated:
        errors.append("catalog/registry.json is out of sync with the repo tree")

    for entry in generated.get("directories", []):
        if not entry.get("approved", True):
            errors.append(f"unapproved top-level directory discovered: {entry['name']}")

    actual_names = {item.name for item in repo_root.iterdir() if item.is_dir()}
    known_names = {entry["name"] for entry in generated.get("directories", [])}
    unknown_on_disk = sorted(name for name in actual_names if name not in known_names and name not in set(generated.get("ignoreTopLevelDirectories", [])))
    if unknown_on_disk:
        errors.extend(f"unknown top-level directory on disk: {name}" for name in unknown_on_disk)

    return errors
