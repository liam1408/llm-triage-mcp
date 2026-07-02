"""Provider-agnostic LLM layer.

One small interface, `complete(system, user) -> str`, with two implementations:

  - AnthropicProvider  — native Anthropic Messages API
  - OpenAIProvider     — OpenAI *and* anything OpenAI-compatible: set base_url to
                         hit Groq, Together, Ollama, LM Studio, vLLM, etc.

Because so many runtimes expose an OpenAI-compatible endpoint, those two classes
cover essentially every hosted or local model. The provider is chosen at runtime
by the LLM_PROVIDER env var, so the rest of the app never knows which model it's
talking to.
"""

import os
from typing import Protocol


class LLMProvider(Protocol):
    """The only thing the rest of the app depends on."""
    def complete(self, system: str, user: str, max_tokens: int = 500) -> str: ...


class AnthropicProvider:
    def __init__(self, model: str, api_key: str | None = None):
        from anthropic import Anthropic
        self.model = model
        self.client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])

    def complete(self, system: str, user: str, max_tokens: int = 500) -> str:
        resp = self.client.messages.create(
            model=self.model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return resp.content[0].text


class OpenAIProvider:
    """OpenAI and any OpenAI-compatible endpoint (base_url switches the target).

    Examples:
        OpenAI:      base_url=None
        Groq:        base_url="https://api.groq.com/openai/v1"
        Together:    base_url="https://api.together.xyz/v1"
        Ollama:      base_url="http://localhost:11434/v1", api_key="ollama"
        LM Studio:   base_url="http://localhost:1234/v1", api_key="lm-studio"
    """
    def __init__(self, model: str, api_key: str | None = None, base_url: str | None = None):
        from openai import OpenAI
        self.model = model
        self.client = OpenAI(
            api_key=api_key or os.environ.get("OPENAI_API_KEY", "not-needed-for-local"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL") or None,
        )

    def complete(self, system: str, user: str, max_tokens: int = 500) -> str:
        resp = self.client.chat.completions.create(
            model=self.model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content


def get_provider() -> LLMProvider:
    """Build the provider from environment variables.

    LLM_PROVIDER   = anthropic | openai   (default: anthropic)
    LLM_MODEL      = model name           (sensible default per provider)
    OPENAI_BASE_URL= set to point OpenAIProvider at a local / third-party endpoint
    """
    provider = os.environ.get("LLM_PROVIDER", "anthropic").lower()
    model = os.environ.get("LLM_MODEL")

    if provider == "anthropic":
        return AnthropicProvider(model or "claude-sonnet-4-6")
    if provider == "openai":
        return OpenAIProvider(model or "gpt-4o-mini")
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r} (use 'anthropic' or 'openai')")
