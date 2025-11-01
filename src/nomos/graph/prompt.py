"""Helpers for building node prompts from graph specs.

Provides utilities to format outgoing edge conditions to include in LLM prompts,
helping the model choose the next step (Decision.MOVE.step_id).
"""

from __future__ import annotations

from typing import List, Optional

from .spec import AgentSpec


def edge_conditions_for_prompt(spec: AgentSpec, current: str) -> str:
    """Return a string listing allowed targets with their natural-language conditions."""
    lines: List[str] = []
    for e in spec.edges:
        if e.from_id == current:
            cond = (e.condition or "(no condition specified)").strip()
            lines.append(f"- to '{e.to_id}': {cond}")
    return "\n".join(lines)


__all__ = ["edge_conditions_for_prompt"]

