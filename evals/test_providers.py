"""Tests for Ticket 3: Provider Abstraction + Routing."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from omega.providers.base import (
    ProviderRouter, ProviderRequest, ProviderResponse, ProviderStatus, RoutingPolicy,
)
from omega.providers.ollama import OllamaProvider
from omega.providers.openai import OpenAIProvider
from omega.providers.anthropic import AnthropicProvider
from omega.providers.google import GoogleProvider


def test_provider_response_normalization():
    """ProviderResponse has consistent structure regardless of provider."""
    r = ProviderResponse(
        text="hello", provider_name="test", model="test-model",
        status=ProviderStatus.SUCCESS, latency_ms=42.0,
    )
    d = r.to_dict()
    assert d["text"] == "hello"
    assert d["provider_name"] == "test"
    assert d["status"] == "success"
    assert r.ok
    print("[PASS] test_provider_response_normalization")


def test_provider_error_normalization():
    """Error responses are normalized."""
    r = ProviderResponse(
        text="", provider_name="test", model="test-model",
        status=ProviderStatus.ERROR, error_message="something broke",
    )
    assert not r.ok
    assert r.error_message == "something broke"
    print("[PASS] test_provider_error_normalization")


def test_missing_credentials_no_crash():
    """Providers without credentials return unavailable, not crash."""
    for ProviderCls in [OpenAIProvider, AnthropicProvider, GoogleProvider]:
        p = ProviderCls(api_key="")
        assert not p.is_available()
        req = ProviderRequest(prompt="test")
        resp = p.generate(req)
        assert resp.status == ProviderStatus.UNAVAILABLE
        assert not resp.ok
    print("[PASS] test_missing_credentials_no_crash")


def test_router_fallback():
    """Router falls back through unavailable providers gracefully."""
    router = ProviderRouter()
    router.register(OpenAIProvider(api_key=""))
    router.register(AnthropicProvider(api_key=""))

    req = ProviderRequest(prompt="test")
    resp = router.route(req, RoutingPolicy.FALLBACK)
    assert resp.status == ProviderStatus.UNAVAILABLE
    assert "All providers failed" in resp.error_message
    print("[PASS] test_router_fallback")


def test_router_explicit_missing():
    """Explicit routing to missing provider returns unavailable."""
    router = ProviderRouter()
    req = ProviderRequest(prompt="test")
    resp = router.route(req, RoutingPolicy.EXPLICIT, provider_name="nonexistent")
    assert resp.status == ProviderStatus.UNAVAILABLE
    print("[PASS] test_router_explicit_missing")


def test_router_available_providers():
    """available_providers returns only those with credentials."""
    router = ProviderRouter()
    router.register(OpenAIProvider(api_key=""))
    router.register(AnthropicProvider(api_key=""))
    available = router.available_providers()
    # Both have empty keys, so neither should be available
    assert "openai" not in available
    assert "anthropic" not in available
    print("[PASS] test_router_available_providers")


def test_request_serialization():
    """ProviderRequest serializes cleanly."""
    req = ProviderRequest(prompt="long " * 100, model="test", run_id="run_123")
    d = req.to_dict()
    assert len(d["prompt"]) <= 200
    assert d["model"] == "test"
    print("[PASS] test_request_serialization")


def test_ollama_provider_interface():
    """OllamaProvider implements the expected interface."""
    p = OllamaProvider(base_url="http://localhost:99999")
    assert p.name == "ollama"
    # Unavailable on bad port
    assert not p.is_available()
    print("[PASS] test_ollama_provider_interface")


if __name__ == "__main__":
    test_provider_response_normalization()
    test_provider_error_normalization()
    test_missing_credentials_no_crash()
    test_router_fallback()
    test_router_explicit_missing()
    test_router_available_providers()
    test_request_serialization()
    test_ollama_provider_interface()
    print("\n  All provider tests passed.")
