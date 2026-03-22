"""
ADCCL — Anti-Drift Cognitive Control Loop.

Implements the drift penalty J, verification score V, and claim budgets.
The control loop: Anchor → Skeleton → Ground → Flesh → Verify → Repair/Refuse.

Specs: ADCCL_DRIFT_PENALTY, ADCCL_VERIFICATION_GATE, ADCCL_GOAL_CONTRACT
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class SupportStatus(Enum):
    SUPPORTED = "supported"
    COMPUTED = "computed"
    HYPOTHETICAL = "hypothetical"
    UNKNOWN = "unknown"


@dataclass
class Claim:
    text: str
    support: SupportStatus
    evidence: Optional[str] = None


class ClaimBudget:
    """Explicit list of claims the system expects to make."""

    def __init__(self):
        self.claims: list[Claim] = []

    def add(self, text: str, support: SupportStatus, evidence: str | None = None):
        self.claims.append(Claim(text, support, evidence))

    def is_valid(self) -> bool:
        """All supported claims must have evidence."""
        return all(
            c.evidence is not None
            for c in self.claims
            if c.support == SupportStatus.SUPPORTED
        )

    def grounding_ratio(self) -> float:
        if not self.claims:
            return 0.0
        grounded = sum(1 for c in self.claims
                       if c.support in (SupportStatus.SUPPORTED, SupportStatus.COMPUTED))
        return grounded / len(self.claims)


@dataclass
class GoalContract:
    """Canonical structured statement of task, scope, and constraints."""
    task: str
    scope: str = ""
    constraints: list[str] = field(default_factory=list)
    success_criteria: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    unknowns: list[str] = field(default_factory=list)


class DriftController:
    """ADCCL verification and drift scoring."""

    def __init__(self, goal: GoalContract, w_s: float = 0.3, w_c: float = 0.4, w_g: float = 0.3):
        self.goal = goal
        self.w_s = w_s
        self.w_c = w_c
        self.w_g = w_g

    def drift_penalty(self, tokens: list[tuple[float, float, float]]) -> float:
        """Compute J over a sequence of (d_s, d_c, g_t) tuples.
        J = Σ(w_s*d_s + w_c*d_c + w_g*g_t)
        """
        return sum(
            self.w_s * ds + self.w_c * dc + self.w_g * gt
            for ds, dc, gt in tokens
        )

    def verify(self, response: str, alpha: float = 0.3, beta: float = 0.3) -> dict:
        """Compute verification score V for a completed draft.
        V = 1 - (h/N + α*(1-c) + β*g)
        """
        words = response.split()
        N = max(len(words), 1)

        # Hallucination proxy: overconfident absolutes
        certainty_words = sum(1 for w in words if w.lower() in
                              {"definitely", "certainly", "absolutely", "always", "never"})

        # Goal relevance proxy
        goal_words = set(self.goal.task.lower().split())
        response_words = set(response.lower().split())
        coverage = len(goal_words & response_words) / max(len(goal_words), 1)

        # Drift proxy: excessive hedging
        hedge_count = sum(1 for w in words if w.lower() in
                          {"perhaps", "maybe", "possibly", "might", "could"})

        h = certainty_words
        c = coverage
        g = hedge_count / N

        V = 1.0 - (h / N + alpha * (1 - c) + beta * g)
        V = max(0.0, min(1.0, V))

        passed = V > 0.4

        return {
            "V": round(V, 4),
            "length": len(words),
            "hallucination_signals": certainty_words,
            "hedge_signals": hedge_count,
            "goal_relevance": round(coverage, 4),
            "passed": passed,
            "outcome": "verified" if passed else "uncertain",
        }
