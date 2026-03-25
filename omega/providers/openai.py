"""OpenAI provider adapter. Environment-gated: requires OPENAI_API_KEY."""

import json
import os
import time
import urllib.request
import urllib.error

from omega.providers.base import BaseProvider, ProviderRequest, ProviderResponse, ProviderStatus


class OpenAIProvider:
    """OpenAI API provider. Safe to instantiate without credentials — is_available() returns False."""

    API_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(self, api_key: str | None = None, default_model: str = "gpt-4o-mini"):
        self._api_key = api_key if api_key is not None else os.environ.get("OPENAI_API_KEY", "")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "openai"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if not self._api_key:
            return ProviderResponse(
                text="", provider_name="openai", model=request.model or self._default_model,
                status=ProviderStatus.UNAVAILABLE, error_message="OPENAI_API_KEY not set",
            )

        model = request.model or self._default_model
        start = time.time()

        messages = []
        if request.system:
            messages.append({"role": "system", "content": request.system})
        messages.append({"role": "user", "content": request.prompt})

        payload = json.dumps({
            "model": model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }).encode()

        req = urllib.request.Request(
            self.API_URL,
            data=payload,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._api_key}",
            },
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                text = data["choices"][0]["message"]["content"]
                usage = data.get("usage", {})
                return ProviderResponse(
                    text=text,
                    provider_name="openai",
                    model=model,
                    status=ProviderStatus.SUCCESS,
                    latency_ms=(time.time() - start) * 1000,
                    token_count=usage.get("completion_tokens", 0),
                    raw_metadata={"usage": usage},
                )
        except urllib.error.HTTPError as e:
            body = e.read().decode() if hasattr(e, 'read') else ""
            return ProviderResponse(
                text="", provider_name="openai", model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=f"HTTP {e.code}: {body[:200]}",
            )
        except Exception as e:
            return ProviderResponse(
                text="", provider_name="openai", model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=str(e),
            )
