"""
Baseline: Plain LLM — No retrieval, no verification, no gating.

Simulates a raw LLM call that simply returns text with no OmegA
pipeline components.  Used as the lowest-bar comparison baseline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from evals.baselines import BaselineResult


class PlainLLMBaseline:
    """
    Baseline that returns raw text with no retrieval, verification, or gating.

    Since we cannot call a live LLM without credentials, this baseline
    simulates the plain-LLM behavior: it takes the query and corpus_docs,
    concatenates relevant doc content as if the LLM had it in-context,
    and returns it with zero safety infrastructure.
    """

    def run(self, query: str, corpus_docs: list[dict]) -> BaselineResult:
        """
        Simulate a plain LLM response.

        corpus_docs: list of dicts with 'content' key (raw source text).
        """
        # Plain LLM just dumps all available content as response
        # No retrieval ranking, no citation, no verification
        if corpus_docs:
            combined = " ".join(d.get("content", "") for d in corpus_docs)
            # Simulate LLM paraphrasing by taking first 500 chars
            response = combined[:500]
        else:
            # Without corpus, LLM might hallucinate
            response = f"Based on my training data, here is what I know about: {query}"

        return BaselineResult(
            query=query,
            response=response,
            citations=[],       # No citations — plain LLM doesn't cite
            mode="raw",
            confidence=0.5,     # Arbitrary — no grounding metric
            verified=False,     # No verification
            gated=False,        # No gating
            truthful=False,     # Cannot confirm truthfulness
            abstained=False,    # Plain LLM never abstains
        )
