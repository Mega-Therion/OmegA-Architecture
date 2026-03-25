"""
OmegA Provider Abstraction — Standardized model provider interface.

All providers implement BaseProvider and return ProviderResponse.
Provider-specific parsing never leaks into upper layers.
"""

from omega.providers.base import (
    BaseProvider,
    ProviderRequest,
    ProviderResponse,
    ProviderError,
    ProviderStatus,
    ProviderRouter,
    RoutingPolicy,
)
from omega.providers.ollama import OllamaProvider
from omega.providers.openai import OpenAIProvider
from omega.providers.anthropic import AnthropicProvider
from omega.providers.google import GoogleProvider
