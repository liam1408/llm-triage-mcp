"""Structured output schemas.

These Pydantic models define the exact shape we force the LLM to return.
Validating the model's JSON against a schema is what turns a freeform text
model into a reliable automation component — if the output doesn't match,
we catch it and repair it instead of shipping garbage downstream.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field


class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class Triage(BaseModel):
    """The structured result of triaging a single piece of text."""

    category: str = Field(description="Short category, e.g. 'bug', 'feature-request', 'question'")
    severity: Severity
    summary: str = Field(description="One-sentence summary of the issue")
    tags: List[str] = Field(default_factory=list, description="Up to 5 short labels")
    action_items: List[str] = Field(default_factory=list, description="Concrete next steps")
