"""Tests. We inject a fake provider so the full pipeline is verified without any
API key or network call — parsing, validation, the repair round-trip, and the
MCP tool wrapper. Because the app depends only on the LLMProvider interface, the
same tests cover every real provider.
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.llm import triage_text, _extract_json
from src.schema import Triage, Severity
from src import server


class FakeProvider:
    """Returns queued replies in order, so we can simulate bad-then-good output."""
    def __init__(self, replies):
        self._replies = list(replies)
        self.calls = 0

    def complete(self, system, user, max_tokens=500):
        self.calls += 1
        return self._replies.pop(0)


VALID = '{"category": "bug", "severity": "high", "summary": "Login fails on Safari", "tags": ["auth","safari"], "action_items": ["reproduce on Safari"]}'


def test_extract_json_handles_fences():
    assert _extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert _extract_json('Here you go: {"a": 1} thanks') == {"a": 1}


def test_triage_valid_first_try():
    p = FakeProvider([VALID])
    result = triage_text("Safari users can't log in", provider=p)
    assert isinstance(result, Triage)
    assert result.severity == Severity.high
    assert result.category == "bug"
    assert p.calls == 1


def test_triage_repairs_bad_json():
    p = FakeProvider(["sorry, here's the answer!", VALID])  # bad, then good
    result = triage_text("Safari login broken", provider=p)
    assert result.summary == "Login fails on Safari"
    assert p.calls == 2  # proves the repair round-trip fired


def test_provider_agnostic():
    # Same code path works no matter which provider object is passed in.
    for replies in ([VALID], ["junk", VALID]):
        assert triage_text("x", provider=FakeProvider(replies)).category == "bug"


def test_mcp_tool_returns_dict():
    p = FakeProvider([VALID])
    server.triage_text = lambda text: __import__("src.llm", fromlist=["triage_text"]).triage_text(text, provider=p)
    out = server.triage_issue("Safari login broken")
    assert out["category"] == "bug"
    assert out["severity"] == "high"


if __name__ == "__main__":
    test_extract_json_handles_fences()
    test_triage_valid_first_try()
    test_triage_repairs_bad_json()
    test_provider_agnostic()
    test_mcp_tool_returns_dict()
    print("All tests passed ✓")
