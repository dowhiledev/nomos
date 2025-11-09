"""Type aliases and core type definitions for Nomos runtime.

This module provides the foundational type definitions used throughout the Nomos
system, including type aliases for provider schemas, frames, tool arguments, and
context passing. These types enable type-safe communication between the orchestrator,
LLM providers, and tool runners.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TypeAlias, Union

from pydantic import BaseModel, Field

from .events import DecisionFrame, TokenFrame
from .tool_events import ToolFrame


# Provider schema can be a single Pydantic model (RESPOND) or a per-tool mapping
ProviderSchema: TypeAlias = Optional[Union[type[BaseModel], Dict[str, type[BaseModel]]]]
"""Type alias for LLM provider response schemas.

Can be either:
- A single Pydantic BaseModel for RESPOND actions
- A dict mapping tool names to their respective Pydantic models for TOOL_CALL actions
- None if no schema validation is needed
"""

# Frames emitted by providers
ProviderFrame: TypeAlias = Union[DecisionFrame, TokenFrame]
"""Type alias for frames streamed from LLM providers.

Represents streaming responses from language models. Includes:
- DecisionFrame: Final decision from the provider (RESPOND, TOOL_CALL, or MOVE)
- TokenFrame: Individual token emissions during streaming
"""

# Frames emitted by tools
ToolFrameUnion: TypeAlias = ToolFrame
"""Type alias for frames emitted by tool execution.

Typed tool execution frames (started, progress, stdout, completed, error).
"""

# Tool arguments passed to tool runners
ToolArgs: TypeAlias = Dict[str, Any]
"""Type alias for tool invocation arguments.

A dictionary of keyword arguments passed to tool functions.
"""


class ToolContext(BaseModel):
    """Context object passed to tool functions during execution.

    Provides tools with access to session information, node context, memory,
    and cancellation signals. All fields are optional; tools should defensively
    check for presence using hasattr() or .get() patterns.

    Attributes:
        cancel_event: Asyncio Event that signals cancellation request.
            Tools should check this periodically and exit cleanly when set.
        session_id: The unique identifier for the current session.
        node_id: The ID of the current node in the agent graph (may be None
            if called outside a graph context).
        memory: Optional session memory identifier for accessing persistent state.

    Example:
        >>> async def my_tool(ctx: ToolContext) -> str:
        ...     if hasattr(ctx, 'session_id'):
        ...         print(f"Running in session {ctx.session_id}")
        ...     return "done"
    """

    cancel_event: Optional[Any] = Field(
        default=None, description="Asyncio Event for cancellation signaling"
    )
    session_id: str = Field(description="Unique session identifier")
    node_id: Optional[str] = Field(
        default=None, description="Current node ID in the agent graph"
    )
    memory: Optional[str] = Field(default=None, description="Session memory identifier")


__all__ = [
    "ProviderSchema",
    "ProviderFrame",
    "ToolFrameUnion",
    "ToolArgs",
    "ToolContext",
]
