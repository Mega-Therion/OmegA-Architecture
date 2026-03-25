"""
ADCCL Answer Object — Source-grounded response with citations and uncertainty.

Every answer produced by OmegA carries:
  - answer text
  - citations (source references + excerpts)
  - confidence score
  - uncertainty flag
  - unresolved questions
  - verifier output
  - mode (grounded / inferred / abstained / bounded)

Low-evidence mode degrades gracefully: abstain, ask for source,
or offer bounded inference rather than hallucinating.

Architecture: ADCCL Phase 4
"""

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omega.retrieval import RetrievedChunk
    from omega.claims import ClaimGraph


class AnswerMode(str, Enum):
    GROUNDED = "grounded"      # citations cover the claim
    INFERRED = "inferred"      # reasoning from context, partial support
    ABSTAINED = "abstained"    # insufficient evidence — no answer given
    BOUNDED = "bounded"        # explicit uncertainty range offered


@dataclass
class Citation:
    source_ref: str
    chunk_id: str
    doc_hash: str | None = None
    excerpt: str = ""
    relevance_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "source_ref": self.source_ref,
            "chunk_id": self.chunk_id,
            "doc_hash": self.doc_hash,
            "excerpt": self.excerpt[:200],
            "relevance_score": round(self.relevance_score, 4),
        }


@dataclass
class VerifierOutput:
    V: float                         # composite verification score [0,1]
    passed: bool
    outcome: str                     # verified | uncertain | rejected
    grounding_ratio: float = 0.0
    hallucination_signals: int = 0
    hedge_signals: int = 0
    goal_relevance: float = 0.0

    def to_dict(self) -> dict:
        return {
            "V": round(self.V, 4),
            "passed": self.passed,
            "outcome": self.outcome,
            "grounding_ratio": round(self.grounding_ratio, 4),
            "hallucination_signals": self.hallucination_signals,
            "hedge_signals": self.hedge_signals,
            "goal_relevance": round(self.goal_relevance, 4),
        }


@dataclass
class AnswerObject:
    """
    Canonical OmegA answer: structured, cited, and verifier-stamped.
    This is the machine-facing form — human surfaces render from this.
    """
    answer_id: str
    text: str
    citations: list[Citation]
    confidence: float
    uncertainty_flag: bool
    verifier: VerifierOutput
    mode: AnswerMode = AnswerMode.GROUNDED
    unresolved_questions: list[str] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    claim_graph: "ClaimGraph | None" = None

    def to_dict(self) -> dict:
        d = {
            "answer_id": self.answer_id,
            "text": self.text,
            "citations": [c.to_dict() for c in self.citations],
            "confidence": round(self.confidence, 4),
            "uncertainty_flag": self.uncertainty_flag,
            "unresolved_questions": self.unresolved_questions,
            "verifier": self.verifier.to_dict(),
            "mode": self.mode.value,
            "generated_at": self.generated_at,
        }
        if self.claim_graph is not None:
            d["claim_graph"] = self.claim_graph.to_dict()
        return d

    @property
    def is_trustworthy(self) -> bool:
        """True only when verifier passed and grounding ratio is non-trivial."""
        return self.verifier.passed and self.verifier.grounding_ratio > 0.3


class AnswerBuilder:
    """
    Constructs AnswerObjects from raw text + retrieved chunks.
    Enforces the low-evidence degradation policy.

    Policy:
      grounding_ratio >= 0.5  → GROUNDED
      grounding_ratio >= 0.2  → INFERRED + uncertainty_flag
      grounding_ratio < 0.2   → ABSTAINED (text replaced with abstention)
    """

    GROUNDED_THRESHOLD = 0.5
    INFERRED_THRESHOLD = 0.2
    CONFIDENCE_SCALE = 0.8   # max confidence when grounded

    def build(
        self,
        query: str,
        raw_text: str,
        retrieved_chunks: list["RetrievedChunk"],
        verifier_dict: dict | None = None,
        unresolved: list[str] | None = None,
    ) -> AnswerObject:
        """
        Build an AnswerObject. Applies degradation policy automatically.

        raw_text: text produced by the model
        retrieved_chunks: RetrievedChunk list from HybridRetriever
        verifier_dict: output of DriftController.verify()
        """
        citations = self._build_citations(retrieved_chunks)
        grounding_ratio = self._grounding_ratio(retrieved_chunks)

        verifier = self._build_verifier(
            verifier_dict or {}, grounding_ratio
        )

        mode, text, uncertainty_flag, confidence = self._apply_policy(
            raw_text, grounding_ratio, verifier
        )

        return AnswerObject(
            answer_id=str(uuid.uuid4()),
            text=text,
            citations=citations,
            confidence=confidence,
            uncertainty_flag=uncertainty_flag,
            verifier=verifier,
            mode=mode,
            unresolved_questions=unresolved or [],
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _build_citations(self, chunks: list["RetrievedChunk"]) -> list[Citation]:
        seen = set()
        result = []
        for chunk in chunks:
            if chunk.chunk_id in seen:
                continue
            seen.add(chunk.chunk_id)
            result.append(Citation(
                source_ref=chunk.source_ref,
                chunk_id=chunk.chunk_id,
                doc_hash=chunk.doc_hash,
                excerpt=chunk.content[:200],
                relevance_score=chunk.score,
            ))
        return result

    def _grounding_ratio(self, chunks: list["RetrievedChunk"]) -> float:
        if not chunks:
            return 0.0
        grounded = sum(1 for c in chunks if c.score > 0.1)
        return grounded / len(chunks)

    def _build_verifier(self, v: dict, grounding_ratio: float) -> VerifierOutput:
        V = v.get("V", 0.0)
        # Boost V by grounding evidence
        V_adjusted = min(1.0, V * 0.7 + grounding_ratio * 0.3)
        passed = V_adjusted > 0.4
        if not passed:
            outcome = "uncertain"
        elif grounding_ratio < self.INFERRED_THRESHOLD:
            outcome = "uncertain"
        else:
            outcome = "verified"
        return VerifierOutput(
            V=V_adjusted,
            passed=passed,
            outcome=outcome,
            grounding_ratio=grounding_ratio,
            hallucination_signals=v.get("hallucination_signals", 0),
            hedge_signals=v.get("hedge_signals", 0),
            goal_relevance=v.get("goal_relevance", 0.0),
        )

    def _apply_policy(
        self,
        raw_text: str,
        grounding_ratio: float,
        verifier: VerifierOutput,
    ) -> tuple[AnswerMode, str, bool, float]:
        """Returns (mode, text, uncertainty_flag, confidence)."""

        if grounding_ratio >= self.GROUNDED_THRESHOLD and verifier.passed:
            return (
                AnswerMode.GROUNDED,
                raw_text,
                False,
                self.CONFIDENCE_SCALE * grounding_ratio,
            )
        elif grounding_ratio >= self.INFERRED_THRESHOLD:
            caveat = (
                "\n\n[Note: This answer is based on partial evidence. "
                "Confidence is limited — treat as inference, not fact.]"
            )
            return (
                AnswerMode.INFERRED,
                raw_text + caveat,
                True,
                self.CONFIDENCE_SCALE * grounding_ratio * 0.5,
            )
        else:
            # Abstain — do not emit the model's raw text
            abstention = (
                "Insufficient source evidence to answer this question confidently. "
                "Please provide a source document or rephrase with more context."
            )
            return (
                AnswerMode.ABSTAINED,
                abstention,
                True,
                0.0,
            )
