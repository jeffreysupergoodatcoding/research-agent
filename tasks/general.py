"""Free-form research goal: agent plans + executes. See PLAN.md §Tasks → General."""
from __future__ import annotations
from typing import Any
from agent.browser_agent import ResearchAgent


async def run(agent: ResearchAgent, *, goal: str, output_schema: type | None = None, max_steps: int = 80) -> Any:
    raise NotImplementedError("See PLAN.md")
