#!/usr/bin/env python3
"""Executable audit for theorem / proof / claim correspondence.

This tool is intentionally narrow: it verifies that the canonical proof
artifacts stay synchronized with one another and with the release gate.
It does not re-prove the theorems; it prevents proof-surface drift.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
THEOREM_IDS = [f"T-{i}" for i in range(1, 11)]

SECTION_RE = re.compile(r"^##\s+(T-\d+):", re.MULTILINE)
CLAIM_ROW_RE = re.compile(r"^\|\s*(T-\d+)\s*\|\s*[^|]+\|\s*([^|]+?)\s*\|", re.MULTILINE)
VERIFY_T10_RE = re.compile(r"T-10 .*EnvelopeCompleteness|EnvelopeClock\.next\(\)", re.MULTILINE)


def read(rel_path: str) -> str:
    path = REPO_ROOT / rel_path
    return path.read_text(encoding="utf-8")


def collect_sections(text: str) -> set[str]:
    return {match.group(1) for match in SECTION_RE.finditer(text)}


def collect_claim_rows(text: str) -> dict[str, str]:
    rows: dict[str, str] = {}
    for match in CLAIM_ROW_RE.finditer(text):
        theorem_id, status = match.groups()
        rows[theorem_id] = status.strip()
    return rows


def fail(messages: list[str]) -> None:
    for msg in messages:
        print(f"!! {msg}")
    raise SystemExit(1)


def main() -> int:
    issues: list[str] = []

    theorem_ledger = read("specs/THEOREM_LEDGER.md")
    proof_map = read("proofs/PROOF_MAP.md")
    claim_ledger = read("publication/CLAIM_LEDGER.md")
    verify_sh = read("verify.sh")

    theorem_sections = collect_sections(theorem_ledger)
    proof_sections = collect_sections(proof_map)
    claim_rows = collect_claim_rows(claim_ledger)

    missing_theorems = [tid for tid in THEOREM_IDS if tid not in theorem_sections]
    if missing_theorems:
        issues.append(f"Theorem ledger missing sections: {', '.join(missing_theorems)}")

    missing_proof = [tid for tid in THEOREM_IDS if tid not in proof_sections]
    if missing_proof:
        issues.append(f"Proof map missing sections: {', '.join(missing_proof)}")

    missing_claim = [tid for tid in THEOREM_IDS if tid not in claim_rows]
    if missing_claim:
        issues.append(f"Claim ledger missing rows: {', '.join(missing_claim)}")

    if claim_rows.get("T-8") != "Conditional":
        issues.append("Claim ledger must keep T-8 as Conditional")

    if claim_rows.get("T-10") != "Tested":
        issues.append("Claim ledger must keep T-10 as Tested")

    if "EnvelopeClock.next()" not in theorem_ledger:
        issues.append("Theorem ledger must mention EnvelopeClock.next() for T-10")

    if "test_version_increments_monotonically" not in proof_map:
        issues.append("Proof map must include the monotonic envelope regression test")

    if "TestEnvelopeCompleteness" not in verify_sh or "T-10" not in verify_sh:
        issues.append("verify.sh must include the T-10 formal invariant gate")

    if "T-8 (ProviderNonCollapse): DEFERRED" not in verify_sh:
        issues.append("verify.sh must keep T-8 deferred under the live Ollama gate")

    print("Proof audit summary")
    print(f"  theorem sections: {len(theorem_sections)}")
    print(f"  proof sections: {len(proof_sections)}")
    print(f"  claim rows: {len(claim_rows)}")
    for tid in THEOREM_IDS:
        print(f"  {tid}: theorem={'yes' if tid in theorem_sections else 'no'}, proof={'yes' if tid in proof_sections else 'no'}, claim={'yes' if tid in claim_rows else 'no'}")

    if issues:
        fail(issues)

    print("Proof audit: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
