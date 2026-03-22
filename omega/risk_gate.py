"""
AEGIS Risk Gate — Quantitative risk-gated action execution.

R(a) = w_p*p + w_d*d + w_a*a - w_m*m
Actions are allowed only if R(a) < tau_consent.

Spec: AEGIS_RISK_CONSENT_SCORING
"""

from dataclasses import dataclass, field


@dataclass
class RiskWeights:
    w_p: float = 0.3   # policy sensitivity weight
    w_d: float = 0.25  # data sensitivity weight
    w_a: float = 0.25  # action irreversibility weight
    w_m: float = 0.2   # mitigation weight


class RiskGate:
    """AEGIS risk scoring and consent gating."""

    BLOCKED_PATTERNS = [
        "delete all", "drop table", "rm -rf", "format disk",
        "ignore your instructions", "ignore your system prompt",
        "sudo rm", "truncate", "destroy",
    ]

    ELEVATED_PATTERNS = [
        "execute", "run", "shell", "sudo", "write", "send",
        "post", "push", "deploy",
    ]

    def __init__(self, weights: RiskWeights | None = None, threshold: float = 0.8):
        self.weights = weights or RiskWeights()
        self.threshold = threshold

    def score(self, action: str) -> float:
        """Compute R(a) for a proposed action string."""
        action_lower = action.lower()
        wt = self.weights

        # Policy sensitivity
        p = 1.0 if any(pat in action_lower for pat in self.BLOCKED_PATTERNS) else 0.1

        # Data sensitivity (heuristic)
        d = 0.5 if any(kw in action_lower for kw in ["password", "secret", "token", "key"]) else 0.1

        # Action irreversibility
        a = 0.8 if any(kw in action_lower for kw in ["delete", "drop", "rm", "destroy"]) else 0.2

        # Mitigations
        m = 0.5 if any(kw in action_lower for kw in ["dry-run", "preview", "confirm"]) else 0.1

        R = wt.w_p * p + wt.w_d * d + wt.w_a * a - wt.w_m * m
        return round(R, 4)

    def is_policy_blocked(self, action: str) -> bool:
        """Hard block: action matches a blocked pattern regardless of score."""
        return any(pat in action.lower() for pat in self.BLOCKED_PATTERNS)

    def gate(self, action: str) -> tuple[bool, float]:
        """Returns (allowed, risk_score). Hard-blocked by policy patterns,
        or soft-blocked if R >= threshold."""
        R = self.score(action)
        if self.is_policy_blocked(action):
            return False, R
        return R < self.threshold, R

    def multi_gate(self, V: float, rho: float, R: float,
                   tau_verify: float = 0.4, theta_allow: float = 0.5) -> tuple[bool, dict]:
        """Unified 3-gate composition: V ∧ ρ ∧ R.

        V:   ADCCL Verifier score (higher = better)
        rho: AEON Bridge risk score (lower = better)
        R:   AEGIS shell risk score (lower = better)
        """
        result = {
            "V": V, "V_pass": V > tau_verify,
            "rho": rho, "rho_pass": rho < theta_allow,
            "R": R, "R_pass": R < self.threshold,
        }
        result["allowed"] = all([result["V_pass"], result["rho_pass"], result["R_pass"]])
        return result["allowed"], result
