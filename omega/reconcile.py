"""
MYELIN Memory Reconciliation — Govern truth over time.

Detects duplicates, conflicting facts, staleness, and manages
canonical promotion/demotion with full audit trail.

Architecture: MYELIN Phase 5
"""

import hashlib
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from omega.memory import MemoryGraph, MemoryNode, Stratum, WritePolicy, POLICY_TO_STRATUM, STRATUM_DECAY
from omega.docstore import DocumentStore, DocumentRecord


class ReconciliationType(str, Enum):
    DUPLICATE = "duplicate"
    CONFLICT = "conflict"
    STALE = "stale"
    PROMOTION = "promotion"
    DEMOTION = "demotion"
    SUPERSEDED = "superseded"


class ReconciliationDecision(str, Enum):
    MERGE = "merge"
    KEEP_EXISTING = "keep_existing"
    KEEP_INCOMING = "keep_incoming"
    PROMOTE = "promote"
    DEMOTE = "demote"
    ARCHIVE = "archive"
    FLAG_FOR_REVIEW = "flag_for_review"


@dataclass
class ReconciliationEvent:
    """Structured audit record for a reconciliation decision."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: ReconciliationType = ReconciliationType.CONFLICT
    decision: ReconciliationDecision = ReconciliationDecision.FLAG_FOR_REVIEW
    node_ids: list[str] = field(default_factory=list)
    doc_ids: list[str] = field(default_factory=list)
    reason: str = ""
    details: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    auto_resolved: bool = False

    def to_dict(self) -> dict:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "decision": self.decision.value,
            "node_ids": self.node_ids,
            "doc_ids": self.doc_ids,
            "reason": self.reason,
            "details": self.details,
            "timestamp": self.timestamp,
            "auto_resolved": self.auto_resolved,
        }


@dataclass
class TemporalWindow:
    """Validity window for a fact."""
    valid_from: float
    valid_until: float | None = None  # None = still valid

    @property
    def is_current(self) -> bool:
        now = time.time()
        if now < self.valid_from:
            return False
        if self.valid_until is not None and now > self.valid_until:
            return False
        return True


@dataclass
class ReconciliationReport:
    """Summary of a reconciliation run."""
    events: list[ReconciliationEvent] = field(default_factory=list)
    duplicates_found: int = 0
    conflicts_found: int = 0
    stale_found: int = 0
    promotions: int = 0
    demotions: int = 0
    elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "event_count": len(self.events),
            "duplicates_found": self.duplicates_found,
            "conflicts_found": self.conflicts_found,
            "stale_found": self.stale_found,
            "promotions": self.promotions,
            "demotions": self.demotions,
            "elapsed_ms": round(self.elapsed_ms, 1),
            "events": [e.to_dict() for e in self.events],
        }


class MemoryReconciler:
    """
    Reconciliation engine for MYELIN memory and document store.

    Detects:
    - Duplicate content (hash-based)
    - Conflicting facts (same source, different content)
    - Stale nodes (access_count == 0 past threshold age)
    - Nodes eligible for promotion/demotion

    Integrates with WritePolicy: canonical promotion requires source_ref.
    """

    # Nodes not accessed within this window are candidates for staleness
    STALE_THRESHOLD_SEC = 86400 * 7  # 7 days

    # Minimum access count to be promotion-eligible
    PROMOTION_MIN_ACCESS = 3

    def __init__(self, memory: MemoryGraph, docstore: DocumentStore | None = None):
        self.memory = memory
        self.docstore = docstore
        self._event_log: list[ReconciliationEvent] = []

    def reconcile(self) -> ReconciliationReport:
        """Run a full reconciliation pass over memory and docstore."""
        start = time.time()
        report = ReconciliationReport()

        self._detect_duplicates(report)
        self._detect_conflicts(report)
        self._detect_stale(report)
        self._detect_promotion_candidates(report)
        self._detect_demotion_candidates(report)

        report.elapsed_ms = (time.time() - start) * 1000
        self._event_log.extend(report.events)
        return report

    def promote(self, node_id: str, source_ref: str, reason: str = "") -> ReconciliationEvent:
        """Promote a node to canonical status."""
        node = self.memory.nodes.get(node_id)
        if not node:
            raise KeyError(f"Node '{node_id}' not found")

        old_stratum = node.stratum
        self.memory.promote(node_id, WritePolicy.CANONICAL, source_ref=source_ref)

        event = ReconciliationEvent(
            event_type=ReconciliationType.PROMOTION,
            decision=ReconciliationDecision.PROMOTE,
            node_ids=[node_id],
            reason=reason or f"Promoted from {old_stratum.value} to canonical",
            details={"old_stratum": old_stratum.value, "source_ref": source_ref},
            auto_resolved=False,
        )
        self._event_log.append(event)
        return event

    def demote(self, node_id: str, target_policy: WritePolicy = WritePolicy.SPECULATIVE,
               reason: str = "") -> ReconciliationEvent:
        """Demote a node to a lower trust stratum."""
        node = self.memory.nodes.get(node_id)
        if not node:
            raise KeyError(f"Node '{node_id}' not found")

        old_stratum = node.stratum
        target_stratum = POLICY_TO_STRATUM[target_policy]
        node.stratum = target_stratum

        event = ReconciliationEvent(
            event_type=ReconciliationType.DEMOTION,
            decision=ReconciliationDecision.DEMOTE,
            node_ids=[node_id],
            reason=reason or f"Demoted from {old_stratum.value} to {target_stratum.value}",
            details={"old_stratum": old_stratum.value, "new_stratum": target_stratum.value},
            auto_resolved=False,
        )
        self._event_log.append(event)
        return event

    def event_log(self) -> list[ReconciliationEvent]:
        return list(self._event_log)

    # ------------------------------------------------------------------
    # Detection passes
    # ------------------------------------------------------------------

    def _detect_duplicates(self, report: ReconciliationReport) -> None:
        """Find nodes with identical content (hash collision)."""
        hash_to_nodes: dict[str, list[str]] = {}
        for nid, node in self.memory.nodes.items():
            h = hashlib.sha256(node.content.encode()).hexdigest()
            hash_to_nodes.setdefault(h, []).append(nid)

        for h, nids in hash_to_nodes.items():
            if len(nids) <= 1:
                continue
            report.duplicates_found += 1
            # Auto-resolve: keep the one with highest stratum, then oldest
            sorted_nodes = sorted(
                nids,
                key=lambda nid: (
                    list(Stratum).index(self.memory.nodes[nid].stratum),
                    self.memory.nodes[nid].created_at,
                ),
            )
            keep = sorted_nodes[0]
            event = ReconciliationEvent(
                event_type=ReconciliationType.DUPLICATE,
                decision=ReconciliationDecision.KEEP_EXISTING,
                node_ids=nids,
                reason=f"Duplicate content detected (hash: {h[:12]}). Keeping node '{keep}'.",
                details={"content_hash": h, "kept": keep, "duplicates": sorted_nodes[1:]},
                auto_resolved=True,
            )
            report.events.append(event)

    def _detect_conflicts(self, report: ReconciliationReport) -> None:
        """Find doc-store conflicts: same URI, different content versions."""
        if not self.docstore:
            return

        for uri, doc_ids in self.docstore._uri_index.items():
            if len(doc_ids) <= 1:
                continue
            # Multiple versions exist — flag if latest differs from previous
            docs = [self.docstore.get_doc(did) for did in doc_ids]
            docs = [d for d in docs if d is not None]
            if len(docs) <= 1:
                continue

            latest = docs[-1]
            previous = docs[-2]
            if latest.doc_hash != previous.doc_hash:
                report.conflicts_found += 1
                event = ReconciliationEvent(
                    event_type=ReconciliationType.CONFLICT,
                    decision=ReconciliationDecision.FLAG_FOR_REVIEW,
                    doc_ids=[d.doc_id for d in docs],
                    reason=f"Conflicting versions for URI '{uri}': v{previous.version} → v{latest.version}",
                    details={
                        "source_uri": uri,
                        "versions": [d.version for d in docs],
                        "hashes": [d.doc_hash[:12] for d in docs],
                    },
                )
                report.events.append(event)

    def _detect_stale(self, report: ReconciliationReport) -> None:
        """Find nodes that haven't been accessed and are past the staleness threshold."""
        now = time.time()
        for nid, node in self.memory.nodes.items():
            if node.stratum == Stratum.CANONICAL:
                continue  # Canonical nodes don't go stale
            age = now - node.created_at
            if age > self.STALE_THRESHOLD_SEC and node.access_count == 0:
                report.stale_found += 1
                event = ReconciliationEvent(
                    event_type=ReconciliationType.STALE,
                    decision=ReconciliationDecision.ARCHIVE,
                    node_ids=[nid],
                    reason=f"Node '{nid}' is {age / 86400:.0f} days old with 0 accesses",
                    details={
                        "age_days": round(age / 86400, 1),
                        "stratum": node.stratum.value,
                        "access_count": node.access_count,
                    },
                    auto_resolved=True,
                )
                report.events.append(event)

    def _detect_promotion_candidates(self, report: ReconciliationReport) -> None:
        """Find non-canonical nodes with enough access to warrant promotion."""
        for nid, node in self.memory.nodes.items():
            if node.stratum == Stratum.CANONICAL:
                continue
            if node.access_count >= self.PROMOTION_MIN_ACCESS:
                report.promotions += 1
                event = ReconciliationEvent(
                    event_type=ReconciliationType.PROMOTION,
                    decision=ReconciliationDecision.FLAG_FOR_REVIEW,
                    node_ids=[nid],
                    reason=(
                        f"Node '{nid}' ({node.stratum.value}) accessed "
                        f"{node.access_count} times — promotion candidate"
                    ),
                    details={
                        "stratum": node.stratum.value,
                        "access_count": node.access_count,
                    },
                )
                report.events.append(event)

    def _detect_demotion_candidates(self, report: ReconciliationReport) -> None:
        """Find speculative nodes with high decay — demotion/archive candidates."""
        for (src, tgt), edge in self.memory.edges.items():
            if edge.staleness > 0.8 and edge.retrieval_util < 0.2:
                src_node = self.memory.nodes.get(src)
                if src_node and src_node.stratum == Stratum.SPECULATIVE:
                    report.demotions += 1
                    event = ReconciliationEvent(
                        event_type=ReconciliationType.DEMOTION,
                        decision=ReconciliationDecision.ARCHIVE,
                        node_ids=[src],
                        reason=(
                            f"Speculative node '{src}' has high staleness "
                            f"({edge.staleness:.2f}) and low utility ({edge.retrieval_util:.2f})"
                        ),
                        details={
                            "staleness": edge.staleness,
                            "retrieval_util": edge.retrieval_util,
                        },
                        auto_resolved=True,
                    )
                    report.events.append(event)
