"""
OmegA Fuzz Harness — MemoryGraph Integrity

Fuzzes node additions, edge additions, EdgeBundle.harden() with extreme
values, retrieval_util bounds, graph consistency, and arbitrary operation
sequences.

Run: python3 -m pytest proofs/fuzz_memory.py -v
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from omega.memory import MemoryGraph, MemoryNode, EdgeBundle, Stratum


# ---------------------------------------------------------------------------
# Fuzz: Node additions with random IDs and content
# ---------------------------------------------------------------------------

class TestFuzzNodeAddition:
    """Random node additions must never crash and must be retrievable."""

    @given(
        st.text(min_size=1, max_size=50),
        st.text(min_size=0, max_size=200),
    )
    @settings(max_examples=100)
    def test_add_node_random(self, node_id, content):
        """Adding a node with arbitrary ID and content must not crash."""
        g = MemoryGraph()
        node = g.add_node(node_id, content)
        assert node.id == node_id
        assert node.content == content
        assert g.node_count == 1
        assert node_id in g.nodes

    @given(st.lists(
        st.tuples(st.text(min_size=1, max_size=20), st.text(min_size=0, max_size=50)),
        min_size=0, max_size=30,
    ))
    @settings(max_examples=100)
    def test_add_many_nodes(self, node_specs):
        """Adding many nodes: count equals number of unique IDs."""
        g = MemoryGraph()
        seen_ids = set()
        for nid, content in node_specs:
            g.add_node(nid, content)
            seen_ids.add(nid)
        assert g.node_count == len(seen_ids)


# ---------------------------------------------------------------------------
# Fuzz: Edge additions between existing/non-existing nodes
# ---------------------------------------------------------------------------

class TestFuzzEdgeAddition:
    """Edge additions with existing and non-existing endpoints."""

    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=20),
        st.floats(min_value=-10.0, max_value=10.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_add_edge_no_crash(self, src, tgt, semantic):
        """Adding an edge must never crash, even if nodes don't exist."""
        g = MemoryGraph()
        edge = g.add_edge(src, tgt, semantic=semantic)
        assert edge.source == src
        assert edge.target == tgt
        assert g.edge_count == 1

    @given(
        st.text(min_size=1, max_size=20),
        st.text(min_size=1, max_size=20),
    )
    @settings(max_examples=100)
    def test_add_edge_between_existing_nodes(self, src, tgt):
        """Edges between existing nodes are properly stored."""
        g = MemoryGraph()
        g.add_node(src, "source content")
        g.add_node(tgt, "target content")
        edge = g.add_edge(src, tgt)
        assert (src, tgt) in g.edges


# ---------------------------------------------------------------------------
# Fuzz: EdgeBundle.harden() with extreme values
# ---------------------------------------------------------------------------

class TestFuzzEdgeHarden:
    """Fuzz harden() with extreme reward and lambda values."""

    @given(st.one_of(
        st.just(0.0),
        st.just(1.0),
        st.just(-1.0),
        st.just(-100.0),
        st.just(100.0),
        st.floats(min_value=-1e6, max_value=1e6, allow_nan=False, allow_infinity=False),
    ))
    @settings(max_examples=100)
    def test_harden_extreme_rewards(self, reward):
        """harden() must not crash with extreme reward values."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.5)
        edge.harden(reward)
        # Must not crash; retrieval_util is a float
        assert isinstance(edge.retrieval_util, float)

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.0, max_value=1.0),
        st.floats(min_value=0.001, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_harden_bounded_inputs_bounded_output(self, q, reward, lam):
        """When q and reward are in [0,1], output stays in [0,1]."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=q)
        edge.harden(reward, lam=lam)
        assert -1e-12 <= edge.retrieval_util <= 1.0 + 1e-12, (
            f"retrieval_util out of bounds: q={q}, r={reward}, "
            f"lam={lam}, result={edge.retrieval_util}"
        )

    def test_harden_zero_reward(self):
        """Hardening with reward=0 must decrease retrieval_util."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.5)
        edge.harden(0.0, lam=0.1)
        assert edge.retrieval_util < 0.5

    def test_harden_one_reward(self):
        """Hardening with reward=1 must increase retrieval_util."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.5)
        edge.harden(1.0, lam=0.1)
        assert edge.retrieval_util > 0.5

    def test_harden_negative_reward(self):
        """Hardening with negative reward must decrease retrieval_util."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.5)
        edge.harden(-1.0, lam=0.1)
        assert edge.retrieval_util < 0.5

    def test_harden_reward_greater_than_one(self):
        """Hardening with reward > 1 can push retrieval_util above initial."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=0.5)
        edge.harden(2.0, lam=0.5)
        assert edge.retrieval_util > 0.5


# ---------------------------------------------------------------------------
# Fuzz: retrieval_util stays bounded [0,1] after hardening
# ---------------------------------------------------------------------------

class TestFuzzRetrievalUtilBounded:
    """After many hardening steps with [0,1] inputs, retrieval_util
    must remain in [0,1]."""

    @given(
        st.floats(min_value=0.0, max_value=1.0),
        st.lists(
            st.floats(min_value=0.0, max_value=1.0),
            min_size=1, max_size=50,
        ),
        st.floats(min_value=0.001, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_bounded_after_many_hardens(self, initial_q, rewards, lam):
        """retrieval_util stays in [0,1] through many harden steps."""
        edge = EdgeBundle(source="a", target="b", retrieval_util=initial_q)
        for r in rewards:
            edge.harden(r, lam=lam)
            assert -1e-12 <= edge.retrieval_util <= 1.0 + 1e-12, (
                f"retrieval_util={edge.retrieval_util} out of [0,1] "
                f"after reward={r}"
            )


# ---------------------------------------------------------------------------
# Fuzz: Graph consistency — all edge endpoints exist in nodes
# ---------------------------------------------------------------------------

class TestFuzzGraphConsistency:
    """After adding nodes and edges between them, all edge endpoints
    must exist in the node set."""

    @given(st.lists(
        st.tuples(
            st.text(min_size=1, max_size=10),
            st.text(min_size=1, max_size=10),
        ),
        min_size=1, max_size=20,
    ))
    @settings(max_examples=100)
    def test_edges_with_nodes_consistent(self, pairs):
        """When nodes are added before edges, all endpoints exist."""
        g = MemoryGraph()
        all_ids = set()
        for src, tgt in pairs:
            all_ids.add(src)
            all_ids.add(tgt)
        for nid in all_ids:
            g.add_node(nid, f"content_{nid}")
        for src, tgt in pairs:
            g.add_edge(src, tgt)

        for (src, tgt), edge in g.edges.items():
            assert src in g.nodes, f"Edge source {src} not in nodes"
            assert tgt in g.nodes, f"Edge target {tgt} not in nodes"


# ---------------------------------------------------------------------------
# Fuzz: No crash on arbitrary operation sequences
# ---------------------------------------------------------------------------

# Strategy for graph operations
_op_add_node = st.tuples(
    st.just("add_node"),
    st.text(min_size=1, max_size=10),
    st.text(min_size=0, max_size=30),
)
_op_add_edge = st.tuples(
    st.just("add_edge"),
    st.text(min_size=1, max_size=10),
    st.text(min_size=1, max_size=10),
)
_op_retrieve = st.tuples(
    st.just("retrieve"),
    st.text(min_size=1, max_size=10),
    st.just(""),
)
_op_harden = st.tuples(
    st.just("harden_path"),
    st.text(min_size=1, max_size=10),
    st.text(min_size=1, max_size=10),
)
_op_decay = st.tuples(
    st.just("decay"),
    st.just(""),
    st.just(""),
)

_graph_ops = st.one_of(_op_add_node, _op_add_edge, _op_retrieve, _op_harden, _op_decay)


class TestFuzzArbitraryOperations:
    """Arbitrary sequences of graph operations must never crash."""

    @given(st.lists(_graph_ops, min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_no_crash_on_random_ops(self, ops):
        """No operation sequence should cause a crash."""
        g = MemoryGraph()
        for op_type, arg1, arg2 in ops:
            if op_type == "add_node":
                g.add_node(arg1, arg2)
            elif op_type == "add_edge":
                g.add_edge(arg1, arg2)
            elif op_type == "retrieve":
                g.retrieve(arg1)  # may return None
            elif op_type == "harden_path":
                g.harden_path([arg1, arg2])
            elif op_type == "decay":
                g.apply_decay()
        # If we get here, no crash occurred
        assert g.node_count >= 0
        assert g.edge_count >= 0
