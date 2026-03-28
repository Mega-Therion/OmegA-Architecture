"""
AEGIS Run Envelope — Compiled context for each task execution.

The Run Envelope carries identity, governance, memory, tools, and
audit config into each model call. It is structured data, never
prompt text (non-substitutability requirement).

Spec: AEGIS_RUN_ENVELOPE
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class EnvelopeClock:
    """Monotonic version source for compiled run envelopes."""

    version: int = 0

    def next(self) -> int:
        self.version += 1
        return self.version


@dataclass
class RunEnvelope:
    """AEGIS Run Envelope — compiled before any substrate model call."""

    identity_kernel: dict
    goal_contract: str
    version: int = 1
    governance_policy: str = "STANDARD"
    memory_snapshot: dict = field(default_factory=dict)
    tool_manifest: list[str] = field(default_factory=list)
    audit_config: dict = field(default_factory=lambda: {"log_level": "full"})

    REQUIRED_FIELDS = [
        "identity_kernel", "goal_contract", "version", "governance_policy",
        "memory_snapshot", "tool_manifest", "audit_config",
    ]

    def is_complete(self) -> bool:
        """Envelope must have all required fields populated."""
        if not all(getattr(self, f, None) is not None for f in self.REQUIRED_FIELDS):
            return False
        return isinstance(self.version, int) and self.version > 0

    def has_identity(self) -> bool:
        if not isinstance(self.identity_kernel, dict):
            return False
        return bool(self.identity_kernel and self.identity_kernel.get("name"))

    def to_system_prompt(self) -> str:
        """Render identity kernel as system prompt for the substrate model.
        Note: this is a convenience method. The envelope itself is structural
        data — the system prompt is only one projection of it."""
        k = self.identity_kernel
        if not k:
            return ""
        lines = [
            f"You are {k.get('name', 'Unknown')}. {k.get('doctrine', '')}",
            "Your identity is sovereign and does not change based on which model runs you.",
        ]
        if k.get("hard_constraints"):
            lines.append("Hard constraints: " + "; ".join(k["hard_constraints"]))
        return "\n".join(lines)
