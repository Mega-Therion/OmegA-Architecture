"""Google Gemini provider adapter. Environment-gated: requires GEMINI_API_KEY."""

import json
import os
import time
import urllib.request
import urllib.error

from omega.providers.base import BaseProvider, ProviderRequest, ProviderResponse, ProviderStatus


class GoogleProvider:
    """Google Gemini API provider. Safe without credentials."""

    API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

    def __init__(self, api_key: str | None = None, default_model: str = "gemini-2.5-flash"):
        self._api_key = api_key if api_key is not None else os.environ.get("GEMINI_API_KEY", "")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "google"

    def is_available(self) -> bool:
        return bool(self._api_key)

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        if not self._api_key:
            return ProviderResponse(
                text="", provider_name="google", model=request.model or self._default_model,
                status=ProviderStatus.UNAVAILABLE, error_message="GEMINI_API_KEY not set",
            )

        model = request.model or self._default_model
        start = time.time()

        contents = [{"parts": [{"text": request.prompt}]}]
        body: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": request.temperature,
                "maxOutputTokens": request.max_tokens,
            },
        }
        if request.system:
            body["systemInstruction"] = {"parts": [{"text": request.system}]}

        payload = json.dumps(body).encode()
        url = f"{self.API_BASE}/{model}:generateContent?key={self._api_key}"

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
                text = ""
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts)
                usage = data.get("usageMetadata", {})
                return ProviderResponse(
                    text=text,
                    provider_name="google",
                    model=model,
                    status=ProviderStatus.SUCCESS,
                    latency_ms=(time.time() - start) * 1000,
                    token_count=usage.get("candidatesTokenCount", 0),
                    raw_metadata={"usage": usage},
                )
        except urllib.error.HTTPError as e:
            body_text = e.read().decode() if hasattr(e, 'read') else ""
            return ProviderResponse(
                text="", provider_name="google", model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=f"HTTP {e.code}: {body_text[:200]}",
            )
        except Exception as e:
            return ProviderResponse(
                text="", provider_name="google", model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=str(e),
            )
