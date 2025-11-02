from __future__ import annotations

from typing import Any, Dict, Optional, TypeAlias, Union

from pydantic import BaseModel

from .events import DecisionFrame, TokenFrame
from .tool_events import ToolFrame


# Provider schema can be a single Pydantic model (RESPOND) or a per-tool mapping
ProviderSchema: TypeAlias = Optional[Union[type[BaseModel], Dict[str, type[BaseModel]]]]

# Frames emitted by providers (transition: dict allowed for adapter compatibility)
ProviderFrame: TypeAlias = Union[DecisionFrame, TokenFrame, Dict[str, Any]]

# Frames emitted by tools (supports dict for compatibility)
ToolFrameUnion: TypeAlias = Union[ToolFrame, Dict[str, Any]]

# Tool arguments passed to tool runners
ToolArgs: TypeAlias = Dict[str, Any]


class ToolContext(BaseModel):
    """Context passed to tools by the runner.

    All fields are optional; tools should test for presence.
    """

    cancel_event: Optional[Any] = None
    session_id: str
    node_id: Optional[str] = None
    memory: Optional[str] = None


__all__ = [
    "ProviderSchema",
    "ProviderFrame",
    "ToolFrameUnion",
    "ToolArgs",
    "ToolContext",
]
