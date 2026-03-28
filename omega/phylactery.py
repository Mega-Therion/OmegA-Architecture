"""
AEON Phylactery — Append-only identity chain.

The Phylactery maintains a hash-chained identity canon. Each commit
contains a doctrine update and links to its parent via SHA-256.
The HEAD hash is the agent's current identity vector.

Spec: AEON_PHYLACTERY
"""

from __future__ import annotations

import json
import hashlib
import time
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class PhylacteryCommit:
    content: str
    parent_hash: str
    timestamp: float = field(default_factory=time.time)
    hash: str = ""

    def __post_init__(self):
        if not self.hash:
            self.hash = hashlib.sha256(
                (self.parent_hash + self.content).encode()
            ).hexdigest()


class Phylactery:
    """Append-only identity chain with tamper detection."""

    def __init__(self, genesis_doctrine: str):
        genesis = PhylacteryCommit(content=genesis_doctrine, parent_hash="")
        self.chain: list[PhylacteryCommit] = [genesis]

    def to_dict(self) -> dict:
        return {
            "chain": [
                {
                    "content": commit.content,
                    "parent_hash": commit.parent_hash,
                    "timestamp": commit.timestamp,
                    "hash": commit.hash,
                }
                for commit in self.chain
            ]
        }

    @classmethod
    def from_dict(cls, payload: dict) -> "Phylactery":
        chain_data = payload.get("chain") or []
        if not chain_data:
            raise ValueError("Phylactery payload must include a non-empty chain.")

        genesis = chain_data[0]
        inst = cls(genesis.get("content", ""))
        inst.chain = []
        for item in chain_data:
            commit = PhylacteryCommit(
                content=item["content"],
                parent_hash=item["parent_hash"],
                timestamp=item.get("timestamp", time.time()),
                hash=item.get("hash", ""),
            )
            if commit.hash != item.get("hash", commit.hash):
                raise ValueError("Phylactery commit hash mismatch during load.")
            inst.chain.append(commit)
        if not inst.verify_chain():
            raise ValueError("Loaded Phylactery chain failed verification.")
        return inst

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "Phylactery":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @property
    def head(self) -> str:
        return self.chain[-1].hash

    @property
    def doctrine(self) -> str:
        return self.chain[-1].content

    def commit(self, content: str) -> str:
        new = PhylacteryCommit(content=content, parent_hash=self.head)
        self.chain.append(new)
        return new.hash

    def verify_chain(self) -> bool:
        """Verify the entire chain is untampered."""
        for i, commit in enumerate(self.chain):
            expected_parent = "" if i == 0 else self.chain[i - 1].hash
            if commit.parent_hash != expected_parent:
                return False
            expected_hash = hashlib.sha256(
                (commit.parent_hash + commit.content).encode()
            ).hexdigest()
            if commit.hash != expected_hash:
                return False
        return True

    def kappa(self, other_head: str) -> float:
        """Continuity metric: 1.0 if heads match, 0.0 otherwise.
        A real implementation would use vector divergence over doctrine fields."""
        return 1.0 if self.head == other_head else 0.0

    def __len__(self):
        return len(self.chain)
