"""MCP server: expose the LLM triage automation as tools an LLM client can call.

Run this and connect it to an MCP client (e.g. Claude Desktop). The model on the
other side can then call `triage_issue` / `batch_triage` as native tools. The
FastMCP decorator style is intentionally FastAPI-shaped — each @mcp.tool() is
one callable endpoint with typed arguments.
"""

from mcp.server.fastmcp import FastMCP

from .llm import triage_text

mcp = FastMCP("llm-triage")


@mcp.tool()
def triage_issue(text: str) -> dict:
    """Classify a bug report / support message / feature request into structured
    fields: category, severity, summary, tags, and action_items.

    Args:
        text: the raw issue text to triage
    """
    return triage_text(text).model_dump()


@mcp.tool()
def batch_triage(texts: list[str]) -> list[dict]:
    """Triage several pieces of text at once. Returns one structured result each.

    Args:
        texts: a list of raw issue texts
    """
    return [triage_text(t).model_dump() for t in texts]


if __name__ == "__main__":
    mcp.run()
