"""Ollama provider adapter."""

import json
import time
import urllib.request
import urllib.error

from omega.providers.base import BaseProvider, ProviderRequest, ProviderResponse, ProviderStatus


class OllamaProvider:
    """Ollama local LLM provider."""

    def __init__(self, base_url: str = "http://localhost:11434", default_model: str = "llama3.2:3b"):
        self._base_url = base_url.rstrip("/")
        self._default_model = default_model

    @property
    def name(self) -> str:
        return "ollama"

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(f"{self._base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=3):
                return True
        except Exception:
            return False

    def generate(self, request: ProviderRequest) -> ProviderResponse:
        model = request.model or self._default_model
        start = time.time()

        payload = json.dumps({
            "model": model,
            "prompt": request.prompt,
            "system": request.system,
            "stream": False,
            "options": {
                "temperature": request.temperature,
                "num_predict": request.max_tokens,
            },
        }).encode()

        req = urllib.request.Request(
            f"{self._base_url}/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read().decode())
                text = data.get("response", "")
                elapsed = (time.time() - start) * 1000
                return ProviderResponse(
                    text=text,
                    provider_name="ollama",
                    model=model,
                    status=ProviderStatus.SUCCESS,
                    latency_ms=elapsed,
                    token_count=data.get("eval_count", 0),
                    raw_metadata={
                        "total_duration": data.get("total_duration"),
                        "load_duration": data.get("load_duration"),
                    },
                )
        except urllib.error.URLError as e:
            return ProviderResponse(
                text="",
                provider_name="ollama",
                model=model,
                status=ProviderStatus.UNAVAILABLE,
                latency_ms=(time.time() - start) * 1000,
                error_message=f"Connection failed: {e}",
            )
        except Exception as e:
            return ProviderResponse(
                text="",
                provider_name="ollama",
                model=model,
                status=ProviderStatus.ERROR,
                latency_ms=(time.time() - start) * 1000,
                error_message=str(e),
            )
