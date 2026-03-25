"""
AEGIS Policy DSL / Governance Configuration.

Loads governance policies from simple YAML files (no external deps).
Validates thresholds and constraint consistency.

Architecture: AEGIS Phase 9
"""

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


class InvalidPolicyError(Exception):
    """Raised when a policy configuration is invalid."""
    pass


@dataclass
class PolicyConfig:
    """Complete governance policy configuration."""
    policy_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = "default"
    version: str = "1.0.0"
    risk_threshold: float = 0.8
    evidence_threshold: float = 0.4
    verifier_threshold: float = 0.4
    capability_allowlist: list[str] = field(default_factory=list)
    capability_denylist: list[str] = field(default_factory=list)
    action_escalation: dict = field(default_factory=dict)
    environment: str = "production"
    auto_approve_below: float = 0.3
    human_required_above: float = 0.7
    max_tokens: int = 4096
    blocked_patterns: list[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "version": self.version,
            "risk_threshold": self.risk_threshold,
            "evidence_threshold": self.evidence_threshold,
            "verifier_threshold": self.verifier_threshold,
            "capability_allowlist": self.capability_allowlist,
            "capability_denylist": self.capability_denylist,
            "action_escalation": self.action_escalation,
            "environment": self.environment,
            "auto_approve_below": self.auto_approve_below,
            "human_required_above": self.human_required_above,
            "max_tokens": self.max_tokens,
            "blocked_patterns": self.blocked_patterns,
            "created_at": self.created_at,
        }


def _parse_yaml(text: str) -> dict:
    """
    Minimal YAML subset parser (stdlib only).

    Handles:
      - key: value (strings, ints, floats, booleans, null)
      - key:
          - item       (lists)
      - key:
          subkey: val  (one-level nested dicts)
    """
    result: dict = {}
    lines = text.split("\n")
    i = 0

    def _cast(v: str) -> Any:
        v = v.strip()
        if v in ("true", "True", "yes", "Yes"):
            return True
        if v in ("false", "False", "no", "No"):
            return False
        if v in ("null", "None", "~", ""):
            return None
        # Remove surrounding quotes
        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
            return v[1:-1]
        try:
            return int(v)
        except ValueError:
            pass
        try:
            return float(v)
        except ValueError:
            pass
        return v

    def _indent(line: str) -> int:
        return len(line) - len(line.lstrip())

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Skip blanks and comments
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        indent = _indent(line)

        # Must be a top-level key: ...
        if ":" not in stripped:
            i += 1
            continue

        colon_pos = stripped.index(":")
        key = stripped[:colon_pos].strip()
        rest = stripped[colon_pos + 1:].strip()

        if rest:
            # Simple key: value
            result[key] = _cast(rest)
            i += 1
        else:
            # Check next lines for list or nested dict
            i += 1
            if i >= len(lines):
                result[key] = None
                continue

            # Peek at next non-blank line
            peek = i
            while peek < len(lines) and not lines[peek].strip():
                peek += 1
            if peek >= len(lines):
                result[key] = None
                continue

            next_stripped = lines[peek].strip()
            next_indent = _indent(lines[peek])

            if next_indent <= indent:
                result[key] = None
                continue

            if next_stripped.startswith("- "):
                # List
                items: list = []
                while i < len(lines):
                    ln = lines[i]
                    ls = ln.strip()
                    if not ls or ls.startswith("#"):
                        i += 1
                        continue
                    if _indent(ln) <= indent:
                        break
                    if ls.startswith("- "):
                        items.append(_cast(ls[2:]))
                        i += 1
                    else:
                        break
                result[key] = items
            else:
                # Nested dict (one level)
                sub: dict = {}
                while i < len(lines):
                    ln = lines[i]
                    ls = ln.strip()
                    if not ls or ls.startswith("#"):
                        i += 1
                        continue
                    if _indent(ln) <= indent:
                        break
                    if ":" in ls:
                        cp = ls.index(":")
                        sk = ls[:cp].strip()
                        sv = ls[cp + 1:].strip()
                        sub[sk] = _cast(sv)
                        i += 1
                    else:
                        break
                result[key] = sub

    return result


class PolicyLoader:
    """Load and validate governance policies from YAML files."""

    @staticmethod
    def load(path: str) -> "PolicyConfig":
        """Load a PolicyConfig from a YAML file."""
        with open(path, "r") as f:
            text = f.read()
        d = _parse_yaml(text)
        return PolicyLoader.from_dict(d)

    @staticmethod
    def validate(config: "PolicyConfig") -> tuple[bool, list[str]]:
        """Validate a PolicyConfig. Returns (valid, list_of_errors)."""
        errors: list[str] = []

        # Threshold range checks
        for name, val in [
            ("risk_threshold", config.risk_threshold),
            ("evidence_threshold", config.evidence_threshold),
            ("verifier_threshold", config.verifier_threshold),
            ("auto_approve_below", config.auto_approve_below),
            ("human_required_above", config.human_required_above),
        ]:
            if not (0.0 <= val <= 1.0):
                errors.append(f"{name} must be in [0.0, 1.0], got {val}")

        if config.auto_approve_below >= config.human_required_above:
            errors.append(
                f"auto_approve_below ({config.auto_approve_below}) must be "
                f"< human_required_above ({config.human_required_above})"
            )

        if config.max_tokens < 1:
            errors.append(f"max_tokens must be >= 1, got {config.max_tokens}")

        # Allowlist/denylist overlap
        overlap = set(config.capability_allowlist) & set(config.capability_denylist)
        if overlap:
            errors.append(f"Capabilities in both allowlist and denylist: {overlap}")

        return (len(errors) == 0, errors)

    @staticmethod
    def from_dict(d: dict) -> "PolicyConfig":
        """Build a PolicyConfig from a flat dict (e.g. parsed YAML)."""
        config = PolicyConfig(
            policy_id=str(d.get("policy_id", uuid.uuid4())),
            name=str(d.get("name", "default")),
            version=str(d.get("version", "1.0.0")),
            risk_threshold=float(d.get("risk_threshold", 0.8)),
            evidence_threshold=float(d.get("evidence_threshold", 0.4)),
            verifier_threshold=float(d.get("verifier_threshold", 0.4)),
            capability_allowlist=d.get("capability_allowlist", []) or [],
            capability_denylist=d.get("capability_denylist", []) or [],
            action_escalation=d.get("action_escalation", {}) or {},
            environment=str(d.get("environment", "production")),
            auto_approve_below=float(d.get("auto_approve_below", 0.3)),
            human_required_above=float(d.get("human_required_above", 0.7)),
            max_tokens=int(d.get("max_tokens", 4096)),
            blocked_patterns=d.get("blocked_patterns", []) or [],
        )
        valid, errors = PolicyLoader.validate(config)
        if not valid:
            raise InvalidPolicyError(f"Invalid policy '{config.name}': {'; '.join(errors)}")
        return config
