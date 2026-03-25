"""
MYELIN Hybrid Retrieval — Vector + Lexical + Metadata search
with context expansion and source grounding.

Without an embedding backend, falls back to TF-IDF-style lexical scoring.
When an embedding function is injected, enables semantic vector search.
Hybrid mode combines both with configurable weights.

Architecture: MYELIN Phase 3
"""

import math
import re
import time
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, TYPE_CHECKING

from omega.docstore import DocumentChunk, DocumentStore

if TYPE_CHECKING:
    from omega.query_planner import QueryPlan


class RetrievalMethod(str, Enum):
    VECTOR = "vector"
    LEXICAL = "lexical"
    HYBRID = "hybrid"
    METADATA = "metadata"


@dataclass
class RetrievedChunk:
    """A retrieved chunk with score, provenance, and expanded context."""
    chunk_id: str
    doc_id: str
    content: str
    context: str        # expanded context (neighboring chunks)
    score: float
    source_ref: str
    doc_hash: str | None
    section: str
    chunk_index: int
    retrieval_method: RetrievalMethod

    def to_dict(self) -> dict:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "content": self.content,
            "context": self.context,
            "score": round(self.score, 4),
            "source_ref": self.source_ref,
            "doc_hash": self.doc_hash,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "retrieval_method": self.retrieval_method.value,
        }


@dataclass
class RetrievalResult:
    """Full retrieval response with metadata."""
    query: str
    chunks: list[RetrievedChunk]
    retrieved_at: float = field(default_factory=time.time)
    retrieval_method: RetrievalMethod = RetrievalMethod.HYBRID
    total_candidates: int = 0
    context_expanded: bool = True

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "chunks": [c.to_dict() for c in self.chunks],
            "retrieved_at": self.retrieved_at,
            "retrieval_method": self.retrieval_method.value,
            "total_candidates": self.total_candidates,
            "context_expanded": self.context_expanded,
        }


EmbedFn = Callable[[str], list[float]]


class HybridRetriever:
    """
    Hybrid retriever over a DocumentStore.

    Lexical path: TF-IDF cosine (no external deps).
    Vector path: cosine similarity on injected embeddings.
    Hybrid: weighted combination of both scores.
    """

    def __init__(
        self,
        store: DocumentStore,
        embed_fn: EmbedFn | None = None,
        lexical_weight: float = 0.4,
        vector_weight: float = 0.6,
        context_window: int = 1,
    ):
        self.store = store
        self.embed_fn = embed_fn
        self.lexical_weight = lexical_weight
        self.vector_weight = vector_weight
        self.context_window = context_window

        # Lexical index: chunk_id → term-frequency dict
        self._tf: dict[str, Counter] = {}
        self._idf: dict[str, float] = {}
        self._index_built = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def execute_plan(self, plan: "QueryPlan") -> RetrievalResult:
        """
        Execute a QueryPlan from the QueryPlanner.

        Strategy dispatch:
        - SIMPLE: single retrieval pass with plan weights
        - MULTI_HOP: iterative retrieve → extract follow-up terms → re-retrieve
        - CONTRADICTION_AWARE: retrieve → check for conflicting chunks → re-retrieve
        - EXHAUSTIVE: run all rewritten queries and merge results
        """
        from omega.query_planner import QueryStrategy

        # Override weights from plan
        orig_lex = self.lexical_weight
        orig_vec = self.vector_weight
        self.lexical_weight = plan.lexical_weight
        self.vector_weight = plan.vector_weight

        try:
            if plan.strategy == QueryStrategy.SIMPLE:
                result = self.retrieve(
                    plan.original_query,
                    top_k=plan.top_k,
                    metadata_filter=plan.metadata_filters or None,
                )

            elif plan.strategy == QueryStrategy.MULTI_HOP:
                result = self._execute_multi_hop(plan)

            elif plan.strategy == QueryStrategy.CONTRADICTION_AWARE:
                result = self._execute_contradiction_aware(plan)

            else:  # EXHAUSTIVE
                result = self._execute_exhaustive(plan)
        finally:
            self.lexical_weight = orig_lex
            self.vector_weight = orig_vec

        return result

    def _execute_multi_hop(self, plan: "QueryPlan") -> RetrievalResult:
        """Multi-hop: iteratively retrieve, extract follow-up terms, re-retrieve."""
        import re as _re

        all_chunks: list[RetrievedChunk] = []
        seen_ids: set[str] = set()
        queries = list(plan.rewritten_queries)

        for hop in range(plan.max_hops):
            if not queries:
                break
            query = queries.pop(0)
            result = self.retrieve(
                query,
                top_k=plan.top_k,
                metadata_filter=plan.metadata_filters or None,
            )
            follow_up_terms: list[str] = []
            for chunk in result.chunks:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    all_chunks.append(chunk)
                # Extract potential follow-up terms from high-scoring chunks
                if chunk.score > plan.escalation_threshold:
                    words = set(_re.findall(r'\b[a-z]{4,}\b', chunk.content.lower()))
                    query_words = set(_re.findall(r'\b[a-z]{4,}\b', query.lower()))
                    new_terms = words - query_words
                    if new_terms:
                        follow_up_terms.extend(list(new_terms)[:3])

            # Add follow-up query if we found new terms
            if follow_up_terms and hop < plan.max_hops - 1:
                follow_up = query + " " + " ".join(follow_up_terms[:5])
                queries.append(follow_up)

        # Sort by score descending, keep top_k
        all_chunks.sort(key=lambda c: c.score, reverse=True)
        all_chunks = all_chunks[:plan.top_k]

        return RetrievalResult(
            query=plan.original_query,
            chunks=all_chunks,
            retrieval_method=RetrievalMethod.HYBRID,
            total_candidates=len(seen_ids),
            context_expanded=True,
        )

    def _execute_contradiction_aware(self, plan: "QueryPlan") -> RetrievalResult:
        """Retrieve, check for conflicting chunks, re-retrieve to resolve."""
        result = self.retrieve(
            plan.original_query,
            top_k=plan.top_k,
            metadata_filter=plan.metadata_filters or None,
        )

        # Check for contradictions: chunks with high scores but low mutual overlap
        chunks = result.chunks
        conflicting_terms: list[str] = []
        for i, ca in enumerate(chunks):
            for cb in chunks[i + 1:]:
                words_a = set(ca.content.lower().split())
                words_b = set(cb.content.lower().split())
                if not words_a or not words_b:
                    continue
                overlap = len(words_a & words_b) / max(len(words_a | words_b), 1)
                if overlap < 0.15 and ca.score > 0.2 and cb.score > 0.2:
                    # Conflicting chunks — gather differentiating terms
                    diff_a = words_a - words_b
                    diff_b = words_b - words_a
                    conflicting_terms.extend(list(diff_a)[:3])
                    conflicting_terms.extend(list(diff_b)[:3])

        if conflicting_terms:
            # Re-retrieve with conflict-resolving query
            resolution_query = plan.original_query + " " + " ".join(set(conflicting_terms[:8]))
            resolution_result = self.retrieve(
                resolution_query,
                top_k=plan.top_k,
                metadata_filter=plan.metadata_filters or None,
            )
            # Merge, dedup, re-sort
            seen = {c.chunk_id for c in chunks}
            for chunk in resolution_result.chunks:
                if chunk.chunk_id not in seen:
                    seen.add(chunk.chunk_id)
                    chunks.append(chunk)
            chunks.sort(key=lambda c: c.score, reverse=True)
            chunks = chunks[:plan.top_k]

        return RetrievalResult(
            query=plan.original_query,
            chunks=chunks,
            retrieval_method=RetrievalMethod.HYBRID,
            total_candidates=result.total_candidates,
            context_expanded=True,
        )

    def _execute_exhaustive(self, plan: "QueryPlan") -> RetrievalResult:
        """Run all rewritten queries, merge and deduplicate results."""
        all_chunks: list[RetrievedChunk] = []
        seen_ids: set[str] = set()
        total_candidates = 0

        for query in plan.rewritten_queries:
            result = self.retrieve(
                query,
                top_k=plan.top_k,
                metadata_filter=plan.metadata_filters or None,
            )
            total_candidates = max(total_candidates, result.total_candidates)
            for chunk in result.chunks:
                if chunk.chunk_id not in seen_ids:
                    seen_ids.add(chunk.chunk_id)
                    all_chunks.append(chunk)

        all_chunks.sort(key=lambda c: c.score, reverse=True)
        all_chunks = all_chunks[:plan.top_k]

        return RetrievalResult(
            query=plan.original_query,
            chunks=all_chunks,
            retrieval_method=RetrievalMethod.HYBRID,
            total_candidates=total_candidates,
            context_expanded=True,
        )

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        method: RetrievalMethod = RetrievalMethod.HYBRID,
        metadata_filter: dict | None = None,
    ) -> RetrievalResult:
        """
        Retrieve top_k chunks for a query using the specified method.
        Always expands context via neighboring chunks.
        """
        all_chunks = self.store.all_chunks()
        if metadata_filter:
            all_chunks = self._apply_metadata_filter(all_chunks, metadata_filter)

        if not all_chunks:
            return RetrievalResult(query=query, chunks=[], total_candidates=0)

        if method == RetrievalMethod.LEXICAL:
            scored = self._lexical_score(query, all_chunks)
        elif method == RetrievalMethod.VECTOR and self.embed_fn:
            scored = self._vector_score(query, all_chunks)
        elif method == RetrievalMethod.HYBRID:
            scored = self._hybrid_score(query, all_chunks)
        else:
            # Fallback to lexical
            scored = self._lexical_score(query, all_chunks)
            method = RetrievalMethod.LEXICAL

        scored.sort(key=lambda x: x[1], reverse=True)
        top = scored[:top_k]

        results = []
        for chunk, score in top:
            doc = self.store.get_doc(chunk.doc_id)
            expanded = self.store.expand_context(chunk.chunk_id, self.context_window)
            results.append(RetrievedChunk(
                chunk_id=chunk.chunk_id,
                doc_id=chunk.doc_id,
                content=chunk.content,
                context=expanded,
                score=score,
                source_ref=doc.source_uri if doc else "",
                doc_hash=doc.doc_hash if doc else None,
                section=chunk.section,
                chunk_index=chunk.chunk_index,
                retrieval_method=method,
            ))

        return RetrievalResult(
            query=query,
            chunks=results,
            retrieval_method=method,
            total_candidates=len(all_chunks),
            context_expanded=True,
        )

    def build_index(self):
        """(Re)build the lexical TF-IDF index over all current chunks."""
        chunks = self.store.all_chunks()
        N = len(chunks)
        if N == 0:
            return

        self._tf = {}
        df: Counter = Counter()

        for chunk in chunks:
            tokens = _tokenize(chunk.content)
            tf = Counter(tokens)
            self._tf[chunk.chunk_id] = tf
            for term in set(tokens):
                df[term] += 1

        self._idf = {
            term: math.log((N + 1) / (count + 1)) + 1
            for term, count in df.items()
        }
        self._index_built = True

    # ------------------------------------------------------------------
    # Scoring internals
    # ------------------------------------------------------------------

    def _lexical_score(
        self, query: str, chunks: list[DocumentChunk]
    ) -> list[tuple[DocumentChunk, float]]:
        if not self._index_built:
            self.build_index()

        q_tokens = _tokenize(query)
        if not q_tokens:
            return [(c, 0.0) for c in chunks]

        q_tf = Counter(q_tokens)
        q_vec = {t: q_tf[t] * self._idf.get(t, 1.0) for t in q_tf}

        results = []
        for chunk in chunks:
            tf = self._tf.get(chunk.chunk_id, Counter())
            d_vec = {t: tf[t] * self._idf.get(t, 1.0) for t in tf}
            score = _cosine(q_vec, d_vec)
            results.append((chunk, score))
        return results

    def _vector_score(
        self, query: str, chunks: list[DocumentChunk]
    ) -> list[tuple[DocumentChunk, float]]:
        assert self.embed_fn is not None
        q_emb = self.embed_fn(query)
        results = []
        for chunk in chunks:
            if not chunk.embedding:
                results.append((chunk, 0.0))
            else:
                score = _cosine_vec(q_emb, chunk.embedding)
                results.append((chunk, score))
        return results

    def _hybrid_score(
        self, query: str, chunks: list[DocumentChunk]
    ) -> list[tuple[DocumentChunk, float]]:
        lex_list = self._lexical_score(query, chunks)
        lex = {c.chunk_id: s for c, s in lex_list}

        if self.embed_fn:
            vec_list = self._vector_score(query, chunks)
            vec = {c.chunk_id: s for c, s in vec_list}
            results = []
            for chunk in chunks:
                score = (
                    self.lexical_weight * lex.get(chunk.chunk_id, 0.0)
                    + self.vector_weight * vec.get(chunk.chunk_id, 0.0)
                )
                results.append((chunk, score))
        else:
            results = lex_list

        return results

    def _apply_metadata_filter(
        self, chunks: list[DocumentChunk], filters: dict
    ) -> list[DocumentChunk]:
        """Filter chunks by doc metadata fields."""
        result = []
        for chunk in chunks:
            doc = self.store.get_doc(chunk.doc_id)
            if doc and all(doc.metadata.get(k) == v for k, v in filters.items()):
                result.append(chunk)
        return result


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _tokenize(text: str) -> list[str]:
    return re.findall(r'\b[a-z]{2,}\b', text.lower())


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    dot = sum(a.get(t, 0) * b.get(t, 0) for t in a)
    mag_a = math.sqrt(sum(v ** 2 for v in a.values()))
    mag_b = math.sqrt(sum(v ** 2 for v in b.values()))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)


def _cosine_vec(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    mag_a = math.sqrt(sum(x ** 2 for x in a))
    mag_b = math.sqrt(sum(y ** 2 for y in b))
    if mag_a == 0 or mag_b == 0:
        return 0.0
    return dot / (mag_a * mag_b)
