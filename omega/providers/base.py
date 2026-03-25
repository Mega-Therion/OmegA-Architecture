"""
Provider base interface and routing engine.

Every provider normalizes its output into ProviderResponse.
The ProviderRouter selects and falls back across providers.
"""

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol


class ProviderStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    UNAVAILABLE = "unavailable"
    TIMEOUT = "timeout"


@dataclass
class ProviderRequest:
    """Normalized request to any provider."""
    prompt: str
    system: str = ""
    model: str = ""
    temperature: float = 0.3
    max_tokens: int = 512
    run_id: str = ""

    def to_dict(self) -> dict:
        return {
            "prompt": self.prompt[:200],
            "system": self.system[:100],
            "model": self.model,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "run_id": self.run_id,
        }


@dataclass
class ProviderResponse:
    """Normalized response from any provider."""
    text: str
    provider_name: str
    model: str
    status: ProviderStatus
    latency_ms: float = 0.0
    token_count: int = 0
    error_message: str = ""
    raw_metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "text": self.text[:500] if self.text else "",
            "provider_name": self.provider_name,
            "model": self.model,
            "status": self.status.value,
            "latency_ms": round(self.latency_ms, 1),
            "token_count": self.token_count,
            "error_message": self.error_message,
        }

    @property
    def ok(self) -> bool:
        return self.status == ProviderStatus.SUCCESS


@dataclass
class ProviderError:
    """Normalized provider error."""
    provider_name: str
    error: str
    status: ProviderStatus = ProviderStatus.ERROR


class BaseProvider(Protocol):
    """Interface that all providers must implement."""

    @property
    def name(self) -> str: ...

    def is_available(self) -> bool: ...

    def generate(self, request: ProviderRequest) -> ProviderResponse: ...


class RoutingPolicy(str, Enum):
    EXPLICIT = "explicit"       # Use the named provider
    FALLBACK = "fallback"       # Try providers in order, use first success
    PREFERRED = "preferred"     # Try preferred first, then fallback list


@dataclass
class RouteDecision:
    provider_name: str
    reason: str
    fallback_chain: list[str] = field(default_factory=list)


class ProviderRouter:
    """
    Routes requests to providers with fallback support.
    Missing credentials do not crash — unavailable providers are skipped.
    """

    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}
        self._preference_order: list[str] = []

    def register(self, provider: BaseProvider) -> None:
        self._providers[provider.name] = provider
        if provider.name not in self._preference_order:
            self._preference_order.append(provider.name)

    def set_preference(self, order: list[str]) -> None:
        self._preference_order = order

    def available_providers(self) -> list[str]:
        return [n for n, p in self._providers.items() if p.is_available()]

    def route(
        self,
        request: ProviderRequest,
        policy: RoutingPolicy = RoutingPolicy.FALLBACK,
        provider_name: str | None = None,
    ) -> ProviderResponse:
        """
        Route a request to a provider.
        - EXPLICIT: use provider_name, fail if unavailable.
        - FALLBACK: try preference order, return first success.
        - PREFERRED: try provider_name first, then fallback.
        """
        if policy == RoutingPolicy.EXPLICIT:
            if not provider_name or provider_name not in self._providers:
                return ProviderResponse(
                    text="",
                    provider_name=provider_name or "unknown",
                    model=request.model,
                    status=ProviderStatus.UNAVAILABLE,
                    error_message=f"Provider '{provider_name}' not registered",
                )
            return self._try_provider(self._providers[provider_name], request)

        # Build attempt order
        if policy == RoutingPolicy.PREFERRED and provider_name:
            order = [provider_name] + [n for n in self._preference_order if n != provider_name]
        else:
            order = list(self._preference_order)

        errors: list[str] = []
        for name in order:
            provider = self._providers.get(name)
            if not provider or not provider.is_available():
                errors.append(f"{name}: unavailable")
                continue

            response = self._try_provider(provider, request)
            if response.ok:
                return response
            errors.append(f"{name}: {response.error_message}")

        return ProviderResponse(
            text="",
            provider_name="none",
            model=request.model,
            status=ProviderStatus.UNAVAILABLE,
            error_message=f"All providers failed: {'; '.join(errors)}",
        )

    def _try_provider(self, provider: BaseProvider, request: ProviderRequest) -> ProviderResponse:
        try:
            return provider.generate(request)
        except Exception as e:
            return ProviderResponse(
                text="",
                provider_name=provider.name,
                model=request.model,
                status=ProviderStatus.ERROR,
                error_message=str(e),
            )
