"""Anthropic provider adapter. Environment-gated: requires ANTHROPIC_API_KEY."""

import json
import os
import time
import urllib.request
import urllib.error

from omega.providers.base import BaseProvider, ProviderRequest, ProviderResponse, ProviderStatus


class AnthropicProvider:
    """Anthropic Claude API provider. Safe without credentials."""

    API_URL = "https://api.anthropic.com/v1/messages"

    def __init__(self, api_key: str | None = None, default_model: str = "claude-sonnet-4-20250514"):
        self._api_key = api_key if api_key is not None else os.environ.get("ANTHROPIC_API_KEY", "")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "anthropic"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if not self._api_key:
            return ProviderResponse(
                text="", provider_name="anthropic", model=request.model or self._default_model,
                status=ProviderStatus.UNAVAILABLE, error_message="ANTHROPIC_API_KEY not set",
            )

        model = request.model or self._default_model
        start = time.time()

        body: dict = {
            "model": model,
            "max_tokens": request.max_tokens,
            "messages": [{"role": "user", "content": request.prompt}],
        }
        if request.system:
            body["system"] = request.system

        payload = json.dumps(body).encode()

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                text = ""
                for block in data.get("content", []):
                    if block.get("type") == "text":
                        text += block.get("text", "")
                usage = data.get("usage", {})
                return ProviderResponse(
                    text=text,
                    provider_name="anthropic",
                    model=model,
                    status=ProviderStatus.SUCCESS,
                    latency_ms=(time.time() - start) * 1000,
                    token_count=usage.get("output_tokens", 0),
                    raw_metadata={"usage": usage},
                )
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if hasattr(e, 'read') else ""
            return ProviderResponse(
                text="", provider_name="anthropic", model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=f"HTTP {e.code}: {body_text[:200]}",
            )
        except Exception as e:
            return ProviderResponse(
                text="", provider_name="anthropic", model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=str(e),
            )
