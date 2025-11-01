"""Typed models for tool runner frames."""

from __future__ import annotations

from typing import Any, Dict, Literal, Optional, Union

from pydantic import BaseModel, Field


class ToolStarted(BaseModel):
    type: Literal["tool.started"] = "tool.started"
    tool: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class ToolProgress(BaseModel):
    type: Literal["tool.progress"] = "tool.progress"
    stage: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class ToolStdout(BaseModel):
    type: Literal["tool.stdout"] = "tool.stdout"
    line: str


class ToolCompleted(BaseModel):
    type: Literal["tool.completed"] = "tool.completed"
    result: Any


class ToolError(BaseModel):
    type: Literal["tool.error"] = "tool.error"
    error: str


ToolFrame = Union[ToolStarted, ToolProgress, ToolStdout, ToolCompleted, ToolError]


def validate_tool_frame(frame: Dict[str, Any]) -> ToolFrame:  # noqa: ANN401
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
