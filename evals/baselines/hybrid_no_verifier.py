"""
Baseline: Hybrid Retrieval without Verifier — Uses HybridRetriever
but skips ADCCL verification and AEGIS gating.

This isolates the value of retrieval quality from verification quality.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from omega.docstore import DocumentStore, DocFormat
from omega.retrieval import HybridRetriever
from omega.answer import AnswerBuilder
from evals.baselines import BaselineResult


class HybridNoVerifier:
    """
    Uses real HybridRetriever and AnswerBuilder but with no verifier
    dict (empty verification), and no governance gating.
    """

    def run(self, query: str, corpus_docs: list[dict]) -> BaselineResult:
        """
        Run hybrid retrieval + answer builder, but skip verification.

        corpus_docs: list of dicts with 'content', 'source_uri' (optional),
                     'title' (optional) keys.
        """
        store = DocumentStore()
        for doc in corpus_docs:
            store.ingest(
                content=doc.get("content", ""),
                source_uri=doc.get("source_uri", "test://hybrid_no_v"),
                format=DocFormat.PLAINTEXT,
                title=doc.get("title", ""),
            )

        retriever = HybridRetriever(store)
        result = retriever.retrieve(query, top_k=5)
        chunks = result.chunks

        if not chunks:
            return BaselineResult(
                query=query,
                response="No relevant information found.",
                citations=[],
                mode="abstained",
                confidence=0.0,
                verified=False,
                gated=False,
                truthful=False,
                abstained=True,
            )

        # Simulate raw response from chunk content
        raw_text = " ".join(c.content for c in chunks[:3])

        # Build answer with EMPTY verifier dict (no drift control)
        builder = AnswerBuilder()
        answer = builder.build(
            query=query,
            raw_text=raw_text,
            retrieved_chunks=chunks,
            verifier_dict={},  # No verification
        )

        citations = [c.source_ref for c in answer.citations if c.source_ref]

        return BaselineResult(
            query=query,
            response=answer.text,
            citations=citations,
            mode=answer.mode.value,
            confidence=answer.confidence,
            verified=False,     # Verification was skipped
            gated=False,        # No governance gating
            truthful=answer.mode.value == "grounded",
            abstained=answer.mode.value == "abstained",
        )
