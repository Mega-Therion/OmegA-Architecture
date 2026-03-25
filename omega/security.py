"""
AEGIS Security / Secret Isolation.

Provides redaction, secret access with prefix isolation, and trust
boundary enforcement. No secret value is ever logged or serialized
in full.

Architecture: AEGIS Phase 9
"""

import copy
import os
import re
from enum import Enum
from typing import Any


# Regex patterns that match common secret formats
REDACT_PATTERNS: list[str] = [
    r"sk-[A-Za-z0-9]{20,}",                    # OpenAI-style keys
    r"key-[A-Za-z0-9]{20,}",                    # Generic API keys
    r"ghp_[A-Za-z0-9]{36,}",                    # GitHub PATs
    r"gho_[A-Za-z0-9]{36,}",                    # GitHub OAuth
    r"glpat-[A-Za-z0-9\-]{20,}",               # GitLab PATs
    r"Bearer\s+[A-Za-z0-9\-._~+/]+=*",         # Bearer tokens
    r"token[\"']?\s*[:=]\s*[\"'][A-Za-z0-9\-._~+/]{16,}[\"']",  # token assignments
    r"password[\"']?\s*[:=]\s*[\"'][^\"']{4,}[\"']",             # password assignments
    r"AKIA[0-9A-Z]{16}",                        # AWS access key IDs
    r"[A-Za-z0-9+/]{40}",                       # AWS secret keys (40-char base64)
    r"xox[bpsar]-[A-Za-z0-9\-]{10,}",          # Slack tokens
]

_COMPILED_PATTERNS = [re.compile(p) for p in REDACT_PATTERNS]


class TrustBoundary(str, Enum):
    INTERNAL = "internal"     # Within OmegA core
    PROVIDER = "provider"     # LLM provider boundary
    EXTERNAL = "external"     # External API / network
    USER = "user"             # Human-facing boundary


# Ordered from most trusted to least trusted
_TRUST_ORDER = {
    TrustBoundary.INTERNAL: 0,
    TrustBoundary.PROVIDER: 1,
    TrustBoundary.EXTERNAL: 2,
    TrustBoundary.USER: 3,
}


class SecretAccessor:
    """
    Safe accessor for secrets stored in environment variables.

    All secrets are read with a configurable prefix (default OMEGA_).
    Values are never returned in full in any log-visible context.
    """

    def __init__(self, env_prefix: str = "OMEGA_"):
        self._prefix = env_prefix

    def get(self, name: str) -> str:
        """Read a secret from the environment. Raises KeyError if missing."""
        full_key = f"{self._prefix}{name}"
        value = os.environ.get(full_key)
        if value is None:
            raise KeyError(f"Secret '{full_key}' not found in environment")
        return value

    def has(self, name: str) -> bool:
        """Check whether a secret exists without reading its value."""
        return f"{self._prefix}{name}" in os.environ

    def _redacted(self, value: str) -> str:
        """Return a redacted representation: first 4 chars + '***'."""
        if len(value) <= 4:
            return "***"
        return value[:4] + "***"

    def get_redacted(self, name: str) -> str:
        """Read a secret and return only its redacted form."""
        return self._redacted(self.get(name))


class Redactor:
    """
    Deep redaction of dicts and strings.

    Redacts both by key name (SENSITIVE_KEYS) and by regex pattern
    (REDACT_PATTERNS).
    """

    SENSITIVE_KEYS: set[str] = {
        "api_key", "apikey", "api_secret",
        "password", "passwd", "secret",
        "token", "access_token", "refresh_token",
        "authorization", "auth_token",
        "private_key", "client_secret",
        "credential", "credentials",
        "connection_string", "database_url",
    }

    @classmethod
    def redact_dict(cls, d: dict) -> dict:
        """Deep-copy a dict with sensitive values replaced by '***REDACTED***'."""
        return cls._redact_value(d)

    @classmethod
    def _redact_value(cls, value: Any) -> Any:
        if isinstance(value, dict):
            result = {}
            for k, v in value.items():
                if isinstance(k, str) and k.lower() in cls.SENSITIVE_KEYS:
                    result[k] = "***REDACTED***"
                else:
                    result[k] = cls._redact_value(v)
            return result
        elif isinstance(value, list):
            return [cls._redact_value(item) for item in value]
        elif isinstance(value, str):
            return cls.redact_string(value)
        else:
            return value

    @classmethod
    def redact_string(cls, s: str) -> str:
        """Replace any pattern-matched secrets in a string."""
        result = s
        for pattern in _COMPILED_PATTERNS:
            result = pattern.sub("***REDACTED***", result)
        return result


def enforce_boundary(
    source: TrustBoundary,
    target: TrustBoundary,
    data: dict,
) -> dict:
    """
    Enforce trust boundary crossing rules.

    When data moves from a more-trusted to a less-trusted boundary,
    all sensitive fields are redacted. Same-level or inward crossings
    pass data through unchanged.
    """
    source_level = _TRUST_ORDER[source]
    target_level = _TRUST_ORDER[target]

    if target_level > source_level:
        # Crossing outward — redact
        return Redactor.redact_dict(data)

    # Same level or inward — pass through (deep copy for safety)
    return copy.deepcopy(data)
