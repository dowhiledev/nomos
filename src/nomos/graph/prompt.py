"""Helpers for building LLM prompts from graph specifications.

This module provides utilities to format agent graph structure (nodes, edges,
routing options) into human-readable text for inclusion in LLM system prompts.
These helpers make it easy for the model to understand available routing options.
"""

from __future__ import annotations

from typing import List

from .spec import AgentSpec


def edge_conditions_for_prompt(spec: AgentSpec, current: str) -> str:
    """Format routing options for a node as human-readable prompt text.

    Generates a bulleted list of available next nodes with their natural-language
    conditions. This text can be included in the LLM's system prompt to explain
    valid routing options.

    Args:
        spec: The AgentSpec containing edges and nodes.
        current: Current node ID.

    Returns:
        Multi-line string with formatted routing options.
        Each line is "- to '<target>': <condition>".

    Example:
        >>> spec = AgentSpec(
        ...     name="bot",
        ...     start="start",
        ...     nodes=[NodeSpec(id="start"), NodeSpec(id="end")],
        ...     edges=[EdgeSpec(from_id="start", to_id="end", condition="Done")]
        ... )
        >>> text = edge_conditions_for_prompt(spec, "start")
        >>> print(text)
        - to 'end': Done
    """
    lines: List[str] = []
    for e in spec.edges:
        if e.from_id == current:
            cond = (e.condition or "(no condition specified)").strip()
            lines.append(f"- to '{e.to_id}': {cond}")
    return "\n".join(lines)


__all__ = ["edge_conditions_for_prompt"]
