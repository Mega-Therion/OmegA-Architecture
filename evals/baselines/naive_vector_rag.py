"""
Baseline: Naive Vector RAG — Retrieval but no verification or gating.

Uses OmegA's real DocumentStore and HybridRetriever for retrieval,
but skips all verification, drift control, and governance gating.
Citations are included but unverified.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever
from evals.baselines import BaselineResult


class NaiveVectorRAG:
    """
    Retrieval-only baseline.  Ingests docs, retrieves top chunks,
    and returns them as the 'answer' with citations but no verification.
    """

    def run(self, query: str, corpus_docs: list[dict]) -> BaselineResult:
        """
        Run naive RAG: ingest -> retrieve -> concatenate top chunks.

        corpus_docs: list of dicts with 'content', 'source_uri' (optional),
                     'title' (optional) keys.
        """
        store = DocumentStore()
        for doc in corpus_docs:
            store.ingest(
                content=doc.get("content", ""),
                source_uri=doc.get("source_uri", "test://naive_rag"),
                format=DocFormat.PLAINTEXT,
                title=doc.get("title", ""),
            )

        retriever = HybridRetriever(store)
        result = retriever.retrieve(query, top_k=5)

        if not result.chunks:
            return BaselineResult(
                query=query,
                response="No relevant information found.",
                citations=[],
                mode="empty",
                confidence=0.0,
                verified=False,
                gated=False,
                truthful=False,
                abstained=True,
            )

        # Concatenate top chunk content as response
        response = "\n\n".join(c.content for c in result.chunks)
        citations = [c.source_ref for c in result.chunks if c.source_ref]

        # Naive confidence: average retrieval score
        avg_score = sum(c.score for c in result.chunks) / len(result.chunks)

        return BaselineResult(
            query=query,
            response=response,
            citations=citations,
            mode="retrieved",
            confidence=avg_score,
            verified=False,     # No verification step
            gated=False,        # No governance gating
            truthful=False,     # Cannot confirm without verifier
            abstained=False,
        )
