"""LLM automation core: turn messy text into validated structured data.

Provider-agnostic — it talks to whatever `LLMProvider` it's given (Anthropic,
OpenAI, or any OpenAI-compatible/local endpoint). The reliability layer is the
same regardless of model: force JSON, validate against the schema, and do one
repair round-trip if the output is malformed. That repair loop matters more with
smaller/local models, which are less reliable at clean JSON.
"""

import json
from pydantic import ValidationError

from .schema import Triage
from .providers import LLMProvider, get_provider

SYSTEM_PROMPT = (
    "You are a triage engine. Given a piece of text (a bug report, support "
    "message, or feature request), classify it. Respond with ONLY a JSON object "
    "matching this schema, no prose, no markdown fences:\n"
    '{"category": str, "severity": "low"|"medium"|"high"|"critical", '
    '"summary": str, "tags": [str], "action_items": [str]}'
)


def _extract_json(text: str) -> dict:
    """Pull a JSON object out of a model response, tolerating stray text/fences."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].removeprefix("json").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found in model response")
    return json.loads(text[start : end + 1])


def triage_text(text: str, provider: LLMProvider | None = None) -> Triage:
    """Classify one piece of text into a validated Triage object.

    Args:
        text:     the raw input to triage
        provider: any LLMProvider (injected so tests pass a fake, and so the
                  same code runs on Anthropic, OpenAI, or a local model)
    """
    provider = provider or get_provider()

    raw = provider.complete(SYSTEM_PROMPT, text)
    try:
        return Triage(**_extract_json(raw))
    except (ValueError, ValidationError, json.JSONDecodeError):
        # One repair attempt: tell the model exactly what it did wrong.
        raw = provider.complete(
            SYSTEM_PROMPT + "\nYour previous reply was not valid JSON. Return ONLY the JSON object.",
            text,
        )
        return Triage(**_extract_json(raw))
