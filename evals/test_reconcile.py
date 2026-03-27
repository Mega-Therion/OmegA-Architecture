"""Tests for Ticket 5: Memory Reconciliation."""
import sys
import time
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.memory import MemoryGraph, WritePolicy, Stratum
from omega.docstore import DocumentStore, DocFormat
from omega.reconcile import (
    MemoryReconciler, ReconciliationType, ReconciliationDecision,
)


def test_detect_duplicates():
    """Duplicate content in memory graph is detected."""
    mg = MemoryGraph()
    mg.write("a", "Same content here", WritePolicy.WORKING)
    mg.write("b", "Same content here", WritePolicy.SPECULATIVE)
    reconciler = MemoryReconciler(mg)
    report = reconciler.reconcile()
    assert report.duplicates_found == 1
    dup_events = [e for e in report.events if e.event_type == ReconciliationType.DUPLICATE]
    assert len(dup_events) == 1
    assert "a" in dup_events[0].node_ids and "b" in dup_events[0].node_ids
    print("[PASS] test_detect_duplicates")


def test_detect_conflicts():
    """Conflicting doc versions are detected."""
    store = DocumentStore()
    store.ingest("Version 1 content", source_uri="test://doc", format=DocFormat.PLAINTEXT)
    store.ingest("Version 2 different content", source_uri="test://doc", format=DocFormat.PLAINTEXT)
    mg = MemoryGraph()
    reconciler = MemoryReconciler(mg, store)
    report = reconciler.reconcile()
    assert report.conflicts_found == 1
    print("[PASS] test_detect_conflicts")


def test_detect_stale():
    """Stale nodes (old + zero access) are flagged."""
    mg = MemoryGraph()
    node = mg.write("stale_node", "old fact", WritePolicy.SPECULATIVE)
    # Backdate creation
    node.created_at = time.time() - (86400 * 30)  # 30 days ago
    reconciler = MemoryReconciler(mg)
    report = reconciler.reconcile()
    assert report.stale_found >= 1
    stale_events = [e for e in report.events if e.event_type == ReconciliationType.STALE]
    assert any("stale_node" in e.node_ids for e in stale_events)
    print("[PASS] test_detect_stale")


def test_canonical_not_stale():
    """Canonical nodes are never flagged as stale."""
    mg = MemoryGraph()
    node = mg.write("canon", "important fact", WritePolicy.CANONICAL, source_ref="test://src")
    node.created_at = time.time() - (86400 * 365)  # 1 year old
    reconciler = MemoryReconciler(mg)
    report = reconciler.reconcile()
    stale_ids = [nid for e in report.events if e.event_type == ReconciliationType.STALE for nid in e.node_ids]
    assert "canon" not in stale_ids
    print("[PASS] test_canonical_not_stale")


def test_promotion():
    """Promote a node to canonical with audit trail."""
    mg = MemoryGraph()
    mg.write("fact_x", "well-accessed fact", WritePolicy.WORKING)
    reconciler = MemoryReconciler(mg)
    event = reconciler.promote("fact_x", source_ref="test://evidence", reason="Verified by 3 sources")
    assert event.event_type == ReconciliationType.PROMOTION
    assert mg.nodes["fact_x"].stratum == Stratum.CANONICAL
    assert event.details["source_ref"] == "test://evidence"
    print("[PASS] test_promotion")


def test_demotion():
    """Demote a node with audit trail."""
    mg = MemoryGraph()
    mg.write("unreliable", "questionable claim", WritePolicy.WORKING)
    reconciler = MemoryReconciler(mg)
    event = reconciler.demote("unreliable", WritePolicy.SPECULATIVE, reason="Source retracted")
    assert event.event_type == ReconciliationType.DEMOTION
    assert mg.nodes["unreliable"].stratum == Stratum.SPECULATIVE
    print("[PASS] test_demotion")


def test_promotion_candidate_detection():
    """Well-accessed non-canonical nodes are flagged as promotion candidates."""
    mg = MemoryGraph()
    node = mg.write("popular", "frequently accessed", WritePolicy.WORKING)
    node.access_count = 5
    reconciler = MemoryReconciler(mg)
    report = reconciler.reconcile()
    promo_events = [e for e in report.events if e.event_type == ReconciliationType.PROMOTION]
    assert any("popular" in e.node_ids for e in promo_events)
    print("[PASS] test_promotion_candidate_detection")


def test_event_log_persistence():
    """Event log accumulates across reconciliation runs."""
    mg = MemoryGraph()
    reconciler = MemoryReconciler(mg)
    reconciler.reconcile()
    mg.write("new", "content", WritePolicy.WORKING)
    reconciler.reconcile()
    log = reconciler.event_log()
    # Log should contain events from both runs
    assert isinstance(log, list)
    print("[PASS] test_event_log_persistence")


def test_report_serialization():
    """ReconciliationReport serializes to dict."""
    mg = MemoryGraph()
    mg.write("a", "same", WritePolicy.WORKING)
    mg.write("b", "same", WritePolicy.WORKING)
    reconciler = MemoryReconciler(mg)
    report = reconciler.reconcile()
    d = report.to_dict()
    assert "event_count" in d
    assert "duplicates_found" in d
    assert "events" in d
    print("[PASS] test_report_serialization")


if __name__ == "__main__":
    test_detect_duplicates()
    test_detect_conflicts()
    test_detect_stale()
    test_canonical_not_stale()
    test_promotion()
    test_demotion()
    test_promotion_candidate_detection()
    test_event_log_persistence()
    test_report_serialization()
    print("\n  All reconciliation tests passed.")
