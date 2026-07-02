# llm-triage-mcp

An **MCP (Model Context Protocol) server** that exposes an **LLM automation** as tools
an LLM client (e.g. Claude Desktop) can call directly. Give it messy text — a bug
report, a support message, a feature request — and it returns **validated structured
data**: category, severity, a one-line summary, tags, and action items.

The point of the project is the reliability layer around the model, not the model call
itself: every response is forced into a JSON schema, validated with Pydantic, and
repaired with a second round-trip if the model returns something malformed.

It is **provider-agnostic** — the same server runs on Anthropic, OpenAI, or any
OpenAI-compatible/local model (Groq, Together, Ollama, LM Studio, vLLM), chosen by
an env var. The app only depends on a small `LLMProvider` interface, so nothing
else changes when you switch models.

## Architecture

```
MCP client (Claude Desktop)
        │  calls tool: triage_issue(text)
        ▼
src/server.py      FastMCP server — registers tools
        ▼
src/llm.py         forces JSON, validates, repairs   (provider-agnostic)
        ▼
src/providers.py   Anthropic | OpenAI | local, chosen by LLM_PROVIDER
        ▼
src/schema.py      Pydantic schema the output must satisfy
```

- `src/schema.py` — the `Triage` schema (the contract the LLM output must match).
- `src/providers.py` — the swappable LLM backends behind one `complete()` interface.
- `src/llm.py` — the automation: prompt → JSON extraction → validation → one repair retry.
- `src/server.py` — exposes `triage_issue` and `batch_triage` as MCP tools.
- `tests/test_server.py` — verifies the pipeline with a **fake provider** (no key needed).

## Switching models

```bash
LLM_PROVIDER=anthropic ANTHROPIC_API_KEY=sk-ant-...            python -m src.server
LLM_PROVIDER=openai    OPENAI_API_KEY=sk-...                   python -m src.server
LLM_PROVIDER=openai    OPENAI_BASE_URL=http://localhost:11434/v1 LLM_MODEL=llama3.1 python -m src.server  # Ollama, local
```

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env      # add your ANTHROPIC_API_KEY
python tests/test_server.py          # runs offline, should print "All tests passed ✓"

# run the MCP server (talks over stdio)
python -m src.server
```

## Connect to Claude Desktop

Add this to your Claude Desktop MCP config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "llm-triage": {
      "command": "python",
      "args": ["-m", "src.server"],
      "cwd": "/absolute/path/to/llm-triage-mcp",
      "env": { "ANTHROPIC_API_KEY": "sk-ant-..." }
    }
  }
}
```

Restart Claude Desktop, then ask it to "triage this bug report: ..." and it will call
the tool.

## What to extend (make it yours)

- Add a `summarize(text)` or `extract_action_items(text)` tool in `server.py`.
- Swap the schema for your own domain (support tickets, PR reviews, log lines).
- Add a thin FastAPI route in front of `triage_text` so it's also a REST service.
