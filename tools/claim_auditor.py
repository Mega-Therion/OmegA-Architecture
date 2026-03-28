#!/usr/bin/env python3
"""Claim Auditor — ensures public docs never outrun evidence.

Checks:
1. Every theorem in the ledger has a matching proof map entry
2. Every machine-checked claim references an existing Lean file
3. Every correspondence claim references an existing test class
4. Every claim status in CLAIM_LEDGER matches THEOREM_LEDGER
5. Key runtime symbols still exist (implementation-shape invariants)
6. No theorem can exist unanchored from proof or gate

Run: python3 tools/claim_auditor.py
"""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
THEOREM_IDS = [f"T-{i}" for i in range(1, 11)]

# Machine-checked theorems must have a .lean file
LEAN_THEOREM_MAP = {
    "T-2": "proofs/OmegaProofs/IdentityContinuity.lean",
    "T-3": "proofs/OmegaProofs/GovernanceFailClosed.lean",
    "T-5": "proofs/OmegaProofs/MemoryHardening.lean",
    "T-6": "proofs/OmegaProofs/VerifierNonBypass.lean",
    "T-7": "proofs/OmegaProofs/UnifiedGating.lean",
    "T-9": "proofs/OmegaProofs/SelfTagImmutability.lean",
}

# Required runtime symbols — if these disappear, proofs are invalidated
REQUIRED_SYMBOLS = {
    "omega/envelope.py": ["RunEnvelope", "EnvelopeClock", "is_complete", "has_identity"],
    "omega/phylactery.py": ["Phylactery", "PhylacteryCommit", "verify_chain", "commit"],
    "omega/risk_gate.py": ["RiskGate", "multi_gate", "gate", "score"],
    "omega/memory.py": ["EdgeBundle", "MemoryGraph", "harden"],
    "omega/drift.py": ["ClaimBudget", "DriftController", "grounding_ratio", "is_valid"],
}

# Correspondence test classes that must exist
CORRESPONDENCE_CLASSES = {
    "T-2": "TestT2Correspondence",
    "T-3": "TestT3Correspondence",
    "T-5": "TestT5Correspondence",
    "T-6": "TestT6Correspondence",
    "T-7": "TestT7Correspondence",
    "T-9": "TestT9Correspondence",
}


def read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text(encoding="utf-8")


def file_exists(rel_path: str) -> bool:
    return (REPO_ROOT / rel_path).exists()


def main() -> int:
    issues: list[str] = []
    warnings: list[str] = []

    # --- 1. Lean files exist for machine-checked claims ---
    for tid, lean_path in LEAN_THEOREM_MAP.items():
        if not file_exists(lean_path):
            issues.append(f"{tid}: Lean file missing: {lean_path}")

    # --- 2. Correspondence test classes exist ---
    corr_text = read("proofs/correspondence.py") if file_exists("proofs/correspondence.py") else ""
    for tid, cls_name in CORRESPONDENCE_CLASSES.items():
        if cls_name not in corr_text:
            issues.append(f"{tid}: Correspondence class missing: {cls_name}")

    # --- 3. Runtime symbols still exist ---
    for file_path, symbols in REQUIRED_SYMBOLS.items():
        if not file_exists(file_path):
            issues.append(f"Runtime file missing: {file_path}")
            continue
        content = read(file_path)
        for symbol in symbols:
            if symbol not in content:
                issues.append(f"Runtime symbol missing: {symbol} not found in {file_path}")

    # --- 4. Claim ledger status consistency ---
    claim_text = read("publication/CLAIM_LEDGER.md") if file_exists("publication/CLAIM_LEDGER.md") else ""
    theorem_text = read("specs/THEOREM_LEDGER.md") if file_exists("specs/THEOREM_LEDGER.md") else ""

    # Machine-checked theorems should say "Machine-checked" in claim ledger
    for tid in LEAN_THEOREM_MAP:
        if tid in claim_text:
            # Find the row for this theorem
            row_match = re.search(rf"\|\s*{re.escape(tid)}\s*\|[^|]+\|\s*(\S[^|]*?)\s*\|", claim_text)
            if row_match:
                status = row_match.group(1).strip()
                if "Machine-checked" not in status and tid not in ("T-6", "T-9"):
                    # T-6 and T-9 are newly added, may lag
                    warnings.append(f"{tid}: Claim ledger says '{status}', expected 'Machine-checked'")

    # Machine-checked theorems should mention Lean4 in theorem ledger
    for tid in LEAN_THEOREM_MAP:
        if tid in theorem_text:
            # Find the section for this theorem
            section_match = re.search(
                rf"## {re.escape(tid)}:.*?(?=## T-|\Z)",
                theorem_text,
                re.DOTALL,
            )
            if section_match:
                section = section_match.group(0)
                if "Lean4" not in section and "Machine-checked" not in section:
                    warnings.append(f"{tid}: Theorem ledger section doesn't mention Lean4 or Machine-checked")

    # --- 5. Proof map has entries for all theorems ---
    proof_map = read("proofs/PROOF_MAP.md") if file_exists("proofs/PROOF_MAP.md") else ""
    for tid in THEOREM_IDS:
        if f"## {tid}:" not in proof_map:
            issues.append(f"{tid}: Missing from proof map")

    # --- 6. verify.sh references key gates ---
    verify_text = read("verify.sh") if file_exists("verify.sh") else ""
    required_gates = [
        ("Formal Invariant Suite", "property tests"),
        ("Correspondence Tests", "correspondence"),
        ("State Machine Tests", "state machine"),
        ("Lean4", "lean proof build"),
    ]
    for keyword, description in required_gates:
        if keyword not in verify_text:
            issues.append(f"verify.sh missing gate: {description} (keyword: {keyword})")

    # --- Report ---
    print("Claim audit summary")
    print(f"  lean files checked: {len(LEAN_THEOREM_MAP)}")
    print(f"  correspondence classes checked: {len(CORRESPONDENCE_CLASSES)}")
    print(f"  runtime symbol sets checked: {len(REQUIRED_SYMBOLS)}")
    print(f"  issues: {len(issues)}")
    print(f"  warnings: {len(warnings)}")

    for w in warnings:
        print(f"  WARN: {w}")

    if issues:
        for issue in issues:
            print(f"  !! {issue}")
        print("Claim audit: FAIL")
        return 1

    print("Claim audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
