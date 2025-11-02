"""Typed models for tool execution frames and events.

This module defines the complete set of frames emitted by tool runners during
execution. These frames form a comprehensive event stream documenting tool
lifecycle: startup, progress, standard output, completion, and errors.

All frames are Pydantic models for validation and serialization compatibility.
"""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field


class ToolStarted(BaseModel):
    """Frame emitted when tool execution begins.
    
    Signals that the tool runner has accepted the tool invocation and is
    preparing or beginning execution.
    
    Attributes:
        type: Literal "tool.started" frame type.
        tool: Name of the tool being executed.
        data: Optional additional context (e.g., environment info).
    """

    type: Literal["tool.started"] = "tool.started"
    tool: Optional[str] = Field(
        default=None,
        description="Tool name"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context"
    )


class ToolProgress(BaseModel):
    """Frame emitted to report tool execution progress.
    
    Allows tools to report intermediate progress without streaming full output.
    Useful for long-running operations.
    
    Attributes:
        type: Literal "tool.progress" frame type.
        stage: Current execution stage or progress description.
        data: Optional additional progress metrics or context.
    """

    type: Literal["tool.progress"] = "tool.progress"
    stage: Optional[str] = Field(
        default=None,
        description="Progress stage description"
    )
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Progress metrics"
    )


class ToolStdout(BaseModel):
    """Frame for standard output lines from tool execution.
    
    Captures tool output (print statements, logs, etc) line by line. Each frame
    represents one newline-terminated line.
    
    Attributes:
        type: Literal "tool.stdout" frame type.
        line: A single line of output (newline may or may not be included).
    """

    type: Literal["tool.stdout"] = "tool.stdout"
    line: str = Field(description="Output line")


class ToolCompleted(BaseModel):
    """Frame emitted when tool execution completes successfully.
    
    Signals successful tool completion and includes the final result value.
    
    Attributes:
        type: Literal "tool.completed" frame type.
        result: The tool's return value (typically a string or dict).
    """

    type: Literal["tool.completed"] = "tool.completed"
    result: Any = Field(description="Tool result")


class ToolError(BaseModel):
    """Frame emitted when tool execution fails.
    
    Signals a tool error or timeout. Should be the final frame in a failed
    execution sequence.
    
    Attributes:
        type: Literal "tool.error" frame type.
        error: Error message describing the failure.
    """

    type: Literal["tool.error"] = "tool.error"
    error: str = Field(description="Error message")


ToolFrame = Union[ToolStarted, ToolProgress, ToolStdout, ToolCompleted, ToolError]
"""Union of all possible tool execution frame types."""


def validate_tool_frame(frame: Dict[str, Any]) -> ToolFrame:  # noqa: ANN401
    """Validate and parse a raw tool frame dict into a typed ToolFrame.
    
    Inspects the "type" field of the frame dict and deserializes to the
    appropriate Pydantic model. Unknown frame types are converted to ToolError.
    
    Args:
        frame: Raw frame dictionary from tool runner.
    
    Returns:
        A typed ToolFrame (ToolStarted, ToolProgress, etc).
    
    Example:
        >>> raw = {"type": "tool.completed", "result": "success"}
        >>> typed = validate_tool_frame(raw)
        >>> isinstance(typed, ToolCompleted)
        True
    """
    t = frame.get("type")
    if t == "tool.started":
        return ToolStarted.model_validate(frame)
    if t == "tool.progress":
        return ToolProgress.model_validate(frame)
    if t == "tool.stdout":
        return ToolStdout.model_validate(frame)
    if t == "tool.completed":
        return ToolCompleted.model_validate(frame)
    if t == "tool.error":
        return ToolError.model_validate(frame)
    # Unknown type: map to error
    return ToolError(error=f"unknown frame type: {t}").model_copy()  # type: ignore[return-value]



__all__ = [
    "ToolStarted",
    "ToolProgress",
    "ToolStdout",
    "ToolCompleted",
    "ToolError",
    "ToolFrame",
    "validate_tool_frame",
]
