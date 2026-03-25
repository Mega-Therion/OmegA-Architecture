"""
Claim Graph + Evidence Linking — Structured claim tracking with contradiction detection.

Every answer's claims are tracked as nodes in a directed graph.
Evidence edges link claims to their support/contradiction relationships.
Uncertainty propagates through contradictions.

Architecture: ADCCL Phase 5 — Claim Accountability
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omega.answer import AnswerObject
    from omega.retrieval import RetrievedChunk


class ClaimType(str, Enum):
    SUPPORTED = "supported"
    INFERRED = "inferred"
    CONTRADICTED = "contradicted"
    UNRESOLVED = "unresolved"


class EdgeRelation(str, Enum):
    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    QUALIFIES = "qualifies"
    SUPERSEDES = "supersedes"


@dataclass
class ClaimNode:
    claim_id: str
    text: str
    claim_type: ClaimType
    support_strength: float  # 0-1
    grounding_strength: float  # 0-1
    source_refs: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "claim_id": self.claim_id,
            "text": self.text,
            "claim_type": self.claim_type.value,
            "support_strength": round(self.support_strength, 4),
            "grounding_strength": round(self.grounding_strength, 4),
            "source_refs": self.source_refs,
            "created_at": self.created_at,
        }


@dataclass
class EvidenceEdge:
    edge_id: str
    source_claim_id: str
    target_claim_id: str
    relation: EdgeRelation
    weight: float  # 0-1
    source_ref: str = ""
    excerpt: str = ""

    def to_dict(self) -> dict:
        return {
            "edge_id": self.edge_id,
            "source_claim_id": self.source_claim_id,
            "target_claim_id": self.target_claim_id,
            "relation": self.relation.value,
            "weight": round(self.weight, 4),
            "source_ref": self.source_ref,
            "excerpt": self.excerpt[:200],
        }


class ClaimGraph:
    """
    Directed graph of claims with evidence edges.
    Tracks support, contradiction, qualification, and supersession.
    """

    def __init__(self):
        self.claims: dict[str, ClaimNode] = {}
        self.edges: list[EvidenceEdge] = []

    def add_claim(self, claim: ClaimNode) -> ClaimNode:
        self.claims[claim.claim_id] = claim
        return claim

    def add_edge(self, edge: EvidenceEdge) -> EvidenceEdge:
        self.edges.append(edge)
        return edge

    def get_contradictions(self) -> list[tuple[ClaimNode, ClaimNode, EvidenceEdge]]:
        """Return all contradiction triples (source_claim, target_claim, edge)."""
        result = []
        for edge in self.edges:
            if edge.relation == EdgeRelation.CONTRADICTS:
                src = self.claims.get(edge.source_claim_id)
                tgt = self.claims.get(edge.target_claim_id)
                if src and tgt:
                    result.append((src, tgt, edge))
        return result

    def get_unresolved(self) -> list[ClaimNode]:
        """Return all claims marked UNRESOLVED."""
        return [c for c in self.claims.values() if c.claim_type == ClaimType.UNRESOLVED]

    def grounding_ratio(self) -> float:
        """Fraction of claims that are grounded (SUPPORTED with grounding_strength > 0.3)."""
        if not self.claims:
            return 0.0
        grounded = sum(
            1 for c in self.claims.values()
            if c.claim_type == ClaimType.SUPPORTED and c.grounding_strength > 0.3
        )
        return grounded / len(self.claims)

    def propagate_uncertainty(self) -> None:
        """
        Reduce support_strength of claims that are contradicted.
        For each contradiction edge, the target claim's support_strength
        is reduced proportionally to the edge weight and the source claim's
        support_strength.
        """
        for edge in self.edges:
            if edge.relation == EdgeRelation.CONTRADICTS:
                target = self.claims.get(edge.target_claim_id)
                source = self.claims.get(edge.source_claim_id)
                if target and source:
                    penalty = edge.weight * source.support_strength * 0.5
                    target.support_strength = max(0.0, target.support_strength - penalty)
                    if target.support_strength < 0.2:
                        target.claim_type = ClaimType.CONTRADICTED

    def to_dict(self) -> dict:
        return {
            "claims": {cid: c.to_dict() for cid, c in self.claims.items()},
            "edges": [e.to_dict() for e in self.edges],
            "grounding_ratio": round(self.grounding_ratio(), 4),
            "total_claims": len(self.claims),
            "total_edges": len(self.edges),
            "contradictions": len(self.get_contradictions()),
            "unresolved": len(self.get_unresolved()),
        }

    @classmethod
    def from_retrieval_and_answer(
        cls,
        answer: "AnswerObject",
        chunks: list["RetrievedChunk"],
    ) -> "ClaimGraph":
        """
        Build a ClaimGraph from an AnswerObject and its source chunks.

        Strategy:
        - Split answer text into sentences as candidate claims.
        - Each chunk becomes a source evidence node.
        - Match claims to chunks by keyword overlap to create SUPPORTS edges.
        - Claims with no chunk support are marked UNRESOLVED.
        - Claims with strong chunk support are SUPPORTED.
        - Claims with weak support are INFERRED.
        """
        graph = cls()

        # Build chunk-level evidence claims
        chunk_claim_ids: dict[str, str] = {}
        for chunk in chunks:
            cid = str(uuid.uuid4())
            node = ClaimNode(
                claim_id=cid,
                text=chunk.content[:300],
                claim_type=ClaimType.SUPPORTED,
                support_strength=min(1.0, chunk.score),
                grounding_strength=min(1.0, chunk.score),
                source_refs=[chunk.source_ref],
            )
            graph.add_claim(node)
            chunk_claim_ids[chunk.chunk_id] = cid

        # Split answer into sentence-level claims
        sentences = _split_sentences(answer.text)
        answer_claim_ids: list[str] = []

        for sentence in sentences:
            if len(sentence.strip()) < 10:
                continue
            acid = str(uuid.uuid4())
            # Score support by keyword overlap with chunks
            best_score = 0.0
            best_chunk_id = None
            sentence_words = set(sentence.lower().split())

            for chunk in chunks:
                chunk_words = set(chunk.content.lower().split())
                if not chunk_words:
                    continue
                overlap = len(sentence_words & chunk_words) / max(len(sentence_words), 1)
                if overlap > best_score:
                    best_score = overlap
                    best_chunk_id = chunk.chunk_id

            # Classify claim
            if best_score >= 0.3:
                claim_type = ClaimType.SUPPORTED
                support_strength = min(1.0, best_score * 1.5)
                grounding_strength = min(1.0, best_score * 1.2)
            elif best_score >= 0.1:
                claim_type = ClaimType.INFERRED
                support_strength = best_score
                grounding_strength = best_score * 0.5
            else:
                claim_type = ClaimType.UNRESOLVED
                support_strength = 0.0
                grounding_strength = 0.0

            source_refs = []
            if best_chunk_id:
                for chunk in chunks:
                    if chunk.chunk_id == best_chunk_id:
                        source_refs = [chunk.source_ref]
                        break

            node = ClaimNode(
                claim_id=acid,
                text=sentence.strip(),
                claim_type=claim_type,
                support_strength=support_strength,
                grounding_strength=grounding_strength,
                source_refs=source_refs,
            )
            graph.add_claim(node)
            answer_claim_ids.append(acid)

            # Create evidence edge from chunk to answer claim
            if best_chunk_id and best_chunk_id in chunk_claim_ids:
                edge = EvidenceEdge(
                    edge_id=str(uuid.uuid4()),
                    source_claim_id=chunk_claim_ids[best_chunk_id],
                    target_claim_id=acid,
                    relation=EdgeRelation.SUPPORTS,
                    weight=best_score,
                    source_ref=source_refs[0] if source_refs else "",
                    excerpt=sentence[:200],
                )
                graph.add_edge(edge)

        # Detect contradictions: answer claims that reference conflicting chunks
        # Two chunks contradict if they both support the same answer claim
        # but have very different content (low mutual overlap)
        for i, chunk_a in enumerate(chunks):
            for chunk_b in chunks[i + 1:]:
                words_a = set(chunk_a.content.lower().split())
                words_b = set(chunk_b.content.lower().split())
                if not words_a or not words_b:
                    continue
                mutual = len(words_a & words_b) / max(len(words_a | words_b), 1)
                # If chunks are very different but both scored, flag contradiction
                if mutual < 0.1 and chunk_a.score > 0.3 and chunk_b.score > 0.3:
                    cid_a = chunk_claim_ids.get(chunk_a.chunk_id)
                    cid_b = chunk_claim_ids.get(chunk_b.chunk_id)
                    if cid_a and cid_b:
                        edge = EvidenceEdge(
                            edge_id=str(uuid.uuid4()),
                            source_claim_id=cid_a,
                            target_claim_id=cid_b,
                            relation=EdgeRelation.CONTRADICTS,
                            weight=1.0 - mutual,
                            source_ref=chunk_a.source_ref,
                            excerpt=f"Low overlap ({mutual:.2f}) between high-scoring chunks",
                        )
                        graph.add_edge(edge)

        return graph


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences on period, question mark, exclamation, or newline."""
    import re
    # Split on sentence-ending punctuation followed by space or end
    parts = re.split(r'(?<=[.!?])\s+|\n+', text)
    return [p.strip() for p in parts if p.strip()]
