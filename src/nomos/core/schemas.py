"""Typed schemas for core message and decision content.

Pydantic v2 models are used to validate inputs and provider outputs.
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from .types import ProviderSchema


class TextPart(BaseModel):
    type: Literal["text"] = "text"
    data: str


class ImagePart(BaseModel):
    type: Literal["image"] = "image"
    data: dict
    mime: Optional[str] = None


ContentPart = Union[TextPart, ImagePart]


class Message(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: Union[str, List[ContentPart]]


class ToolCall(BaseModel):
    tool_name: str
    tool_kwargs: dict = Field(default_factory=dict)
    tool_kwargs_parsed: Optional[dict] = None


class RespondPayload(BaseModel):
    action: Literal["RESPOND"] = "RESPOND"
    response: str
    parsed: Optional[dict] = None


class ToolCallPayload(BaseModel):
    action: Literal["TOOL_CALL"] = "TOOL_CALL"
    tool_call: ToolCall


DecisionPayload = Union[RespondPayload, ToolCallPayload]


class Checkpoint(BaseModel):
    """Checkpoint data for session state persistence."""

    id: str
    node_id: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)


class SessionInput(BaseModel):
    """Input data for session processing."""

    messages: List[Union[Message, Dict[str, Any]]] = Field(default_factory=list)
    response_schema: Optional[ProviderSchema] = None

    model_config = ConfigDict(extra="allow")


class ControlCommand(BaseModel):
    """Control commands for session management."""

    type: str
    id: Optional[str] = None


__all__ = [
    "TextPart",
    "ImagePart",
    "ContentPart",
    "Message",
    "ToolCall",
    "RespondPayload",
    "ToolCallPayload",
    "DecisionPayload",
    "Checkpoint",
    "SessionInput",
    "ControlCommand",
]
