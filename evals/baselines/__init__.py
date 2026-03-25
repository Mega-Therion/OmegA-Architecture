"""
OmegA Baseline Comparison Framework

Shared BaselineResult dataclass for all baseline implementations.
"""

from dataclasses import dataclass, field


@dataclass
class BaselineResult:
    """Standardized result from any baseline system."""
    query: str
    response: str
    citations: list[str] = field(default_factory=list)
    mode: str = "unknown"
    confidence: float = 0.0
    verified: bool = False
    gated: bool = False
    truthful: bool = False
    abstained: bool = False

    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "response": self.response[:500],
            "citations": self.citations,
            "mode": self.mode,
            "confidence": round(self.confidence, 4),
            "verified": self.verified,
            "gated": self.gated,
            "truthful": self.truthful,
            "abstained": self.abstained,
        }
