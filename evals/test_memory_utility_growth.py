#!/usr/bin/env python3
"""Memory utility growth regression test."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.memory import MemoryGraph, Stratum


def test_memory_utility_growth():
    memory = MemoryGraph()
    memory.add_node("a", "start", stratum=Stratum.OPERATIONAL)
    memory.add_node("b", "middle", stratum=Stratum.OPERATIONAL)
    memory.add_node("c", "cold-start", stratum=Stratum.SPECULATIVE)
    memory.add_node("d", "cold-end", stratum=Stratum.SPECULATIVE)
    hot_edge = memory.add_edge("a", "b", semantic=0.9)
    cold_edge = memory.add_edge("c", "d", semantic=0.1)

    baseline_hot = hot_edge.retrieval_util
    baseline_cold = cold_edge.retrieval_util

    for _ in range(5):
        assert memory.retrieve("a") is not None
        assert memory.retrieve("b") is not None
        memory.harden_path(["a", "b"], reward=1.0)

    memory.apply_decay(dt=10.0)

    assert memory.nodes["a"].retrieval_count >= 5
    assert memory.nodes["b"].retrieval_count >= 5
    assert hot_edge.retrieval_util > baseline_hot
    assert hot_edge.coactivation >= 5
    assert hot_edge.staleness > 0.0
    assert cold_edge.retrieval_util == baseline_cold
    assert cold_edge.staleness > hot_edge.staleness
    assert hot_edge.retrieval_util > cold_edge.retrieval_util

    print("[PASS] memory utility growth")


if __name__ == "__main__":
    test_memory_utility_growth()
