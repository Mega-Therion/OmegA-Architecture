"""
MYELIN — Path-Dependent Graph Memory.

Sparse graph with bundled edge signals, strata-based decay,
and hardening through successful retrieval.

Specs: MYELIN_GRAPH_MEMORY, MYELIN_EDGE_BUNDLES, MYELIN_SPATIAL_STABILIZATION
"""

import time
from dataclasses import dataclass, field
from enum import Enum


class Stratum(Enum):
    CANONICAL = "canonical"
    OPERATIONAL = "operational"
    EPISODIC = "episodic"
    SPECULATIVE = "speculative"


STRATUM_DECAY = {
    Stratum.CANONICAL: 0.0,
    Stratum.OPERATIONAL: 0.01,
    Stratum.EPISODIC: 0.05,
    Stratum.SPECULATIVE: 0.2,
}


@dataclass
class MemoryNode:
    id: str
    content: str
    stratum: Stratum = Stratum.EPISODIC
    embedding: list[float] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class EdgeBundle:
    """Bundled relationship between two memory nodes."""
    source: str
    target: str
    semantic: float = 0.0       # s_ij: semantic similarity
    coactivation: int = 0       # c_ij: co-retrieval count
    retrieval_util: float = 0.5 # q_ij: retrieval utility
    staleness: float = 0.0      # δ_ij: time since last access

    def harden(self, reward: float, lam: float = 0.1):
        """q(t+1) = (1-λ)*q(t) + λ*r"""
        self.retrieval_util = (1 - lam) * self.retrieval_util + lam * reward
        if reward > 0:
            self.coactivation += 1
            self.staleness = 0.0

    def decay(self, dt: float, rate: float):
        """Apply time-based decay to staleness."""
        self.staleness += dt * rate


class MemoryGraph:
    """Sparse path-dependent memory graph."""

    def __init__(self):
        self.nodes: dict[str, MemoryNode] = {}
        self.edges: dict[tuple[str, str], EdgeBundle] = {}

    def add_node(self, id: str, content: str, stratum: Stratum = Stratum.EPISODIC,
                 embedding: list[float] | None = None) -> MemoryNode:
        node = MemoryNode(id=id, content=content, stratum=stratum,
                          embedding=embedding or [])
        self.nodes[id] = node
        return node

    def add_edge(self, source: str, target: str, semantic: float = 0.0) -> EdgeBundle:
        edge = EdgeBundle(source=source, target=target, semantic=semantic)
        self.edges[(source, target)] = edge
        return edge

    def retrieve(self, node_id: str) -> MemoryNode | None:
        """Retrieve a node and record access."""
        node = self.nodes.get(node_id)
        if node:
            node.access_count += 1
        return node

    def harden_path(self, path: list[str], reward: float = 1.0):
        """Harden all edges along a retrieval path."""
        for i in range(len(path) - 1):
            key = (path[i], path[i + 1])
            if key in self.edges:
                self.edges[key].harden(reward)

    def apply_decay(self, dt: float = 1.0):
        """Apply stratum-based decay to all edges."""
        for (src, _), edge in self.edges.items():
            src_node = self.nodes.get(src)
            if src_node:
                rate = STRATUM_DECAY.get(src_node.stratum, 0.05)
                edge.decay(dt, rate)

    def neighbors(self, node_id: str) -> list[tuple[str, EdgeBundle]]:
        """Get all neighbors of a node with their edge bundles."""
        result = []
        for (src, tgt), edge in self.edges.items():
            if src == node_id:
                result.append((tgt, edge))
            elif tgt == node_id:
                result.append((src, edge))
        return result

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
