"""Typed schemas for core message, decision, and checkpoint content.

This module defines Pydantic v2 models for the major domain objects that flow
through the Nomos orchestrator. All models support validation and serialization,
enabling safe type-safe communication between components.

Key models:
- Message/ContentPart: User and assistant messages with rich content support
- Decision/DecisionPayload: LLM decision outcomes (RESPOND, TOOL_CALL, MOVE)
- ToolCall: Tool invocation specification with schema validation
- Checkpoint: Session state persistence for interruption/replay
- SessionInput/ControlCommand: API payloads for orchestrator control
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from .types import ProviderSchema


class TextPart(BaseModel):
    """Text content part of a message.

    Represents a plain text portion of message content. Can be combined with
    other content types (ImagePart) to create rich multi-modal messages.

    Attributes:
        type: Literal "text" identifying this as a text part.
        data: The actual text content.
    """

    type: Literal["text"] = "text"
    data: str = Field(description="Text content")


class ImagePart(BaseModel):
    """Image content part of a message.

    Represents an image portion of message content. Supports both URL-based
    references and embedded data.

    Attributes:
        type: Literal "image" identifying this as an image part.
        data: Image reference (URL or embedded data structure).
        mime: Optional MIME type (e.g., "image/jpeg").
    """

    type: Literal["image"] = "image"
    data: dict = Field(description="Image reference or embedded data")
    mime: Optional[str] = Field(default=None, description="Optional MIME type")


ContentPart = Union[TextPart, ImagePart]
"""Type for message content parts.

Union of all supported content part types. Can be extended with additional
types (audio, video, etc.) as needed.
"""


class Message(BaseModel):
    """A single message in a conversation.

    Represents a message from a user, assistant, or system role. Supports both
    plain text and rich content (images, etc).

    Attributes:
        role: Message origin - "user" (input), "assistant" (model response),
            or "system" (instructions/context).
        content: Message body - either plain text or a list of content parts.

    Example:
        >>> msg1 = Message(role="user", content="What's the weather?")
        >>> msg2 = Message(
        ...     role="user",
        ...     content=[
        ...         TextPart(data="Describe this image:"),
        ...         ImagePart(data={"url": "https://..."})
        ...     ]
        ... )
    """

    role: Literal["user", "assistant", "system"] = Field(
        description="Message originator role"
    )
    content: Union[str, List[ContentPart]] = Field(
        description="Message body (text or content parts)"
    )


class ToolCall(BaseModel):
    """Specification for invoking a tool.

    Represents the LLM's decision to call a specific tool with arguments.
    Includes both raw and parsed argument forms for flexibility and validation.

    Attributes:
        tool_name: The unique identifier of the tool to invoke.
        tool_kwargs: Raw argument dict as provided by the model.
        tool_kwargs_parsed: Optional pre-validated arguments (model-specific).

    Example:
        >>> tc = ToolCall(
        ...     tool_name="weather.get",
        ...     tool_kwargs={"location": "NYC"},
        ...     tool_kwargs_parsed={"location": "NYC"}
        ... )
    """

    tool_name: str = Field(description="Unique tool identifier")
    tool_kwargs: dict = Field(
        default_factory=dict, description="Tool arguments as dict"
    )
    tool_kwargs_parsed: Optional[dict] = Field(
        default=None, description="Pre-validated tool arguments (optional)"
    )


class RespondPayload(BaseModel):
    """Payload for RESPOND action.

    Indicates the agent has generated a final response to the user without
    invoking tools or routing to another node.

    Attributes:
        action: Literal "RESPOND" action type.
        response: The text response to return to the user.
        parsed: Optional parsed/structured version of response.
    """

    action: Literal["RESPOND"] = "RESPOND"
    response: str = Field(description="Text response to user")
    parsed: Optional[dict] = Field(
        default=None, description="Optional parsed/structured response"
    )


class ToolCallPayload(BaseModel):
    """Payload for TOOL_CALL action.

    Indicates the agent has decided to invoke a tool. The orchestrator will
    execute the tool and feed results back to the LLM.

    Attributes:
        action: Literal "TOOL_CALL" action type.
        tool_call: ToolCall specification with name and arguments.
    """

    action: Literal["TOOL_CALL"] = "TOOL_CALL"
    tool_call: ToolCall = Field(description="Tool invocation specification")


class MovePayload(BaseModel):
    """Payload for MOVE action.

    Indicates the agent has decided to route to another node in the graph.
    The orchestrator validates the target against available edges.

    Attributes:
        action: Literal "MOVE" action type.
        step_id: ID of the target node to route to.
    """

    action: Literal["MOVE"] = "MOVE"
    step_id: str = Field(description="Target node ID")


DecisionPayload = Union[RespondPayload, ToolCallPayload, MovePayload]
"""Union of all possible decision actions."""


class Checkpoint(BaseModel):
    """Checkpoint for session state persistence.

    Captures session state at a node boundary, enabling session interruption,
    resumption, and deterministic replay. Multiple checkpoints can exist per
    session, identified by checkpoint.id.

    Attributes:
        id: Unique checkpoint identifier within the session.
        node_id: The node where this checkpoint was created.
        data: Arbitrary session state data to persist.

    Example:
        >>> cp = Checkpoint(
        ...     id="cp_001",
        ...     node_id="gather_requirements",
        ...     data={"requirements": ["fast", "secure"]}
        ... )
    """

    id: str = Field(description="Unique checkpoint identifier")
    node_id: Optional[str] = Field(
        default=None, description="Node ID where checkpoint was created"
    )
    data: Dict[str, Any] = Field(default_factory=dict, description="Session state data")


class SessionInput(BaseModel):
    """Input data for session processing.

    API payload for submitting new input to a session. Includes messages and
    optional response schema for structured output validation.

    Attributes:
        messages: List of Message objects or dicts (for flexibility).
        response_schema: Optional ProviderSchema for validating responses.

    Example:
        >>> inp = SessionInput(
        ...     messages=[Message(role="user", content="Hello!")]
        ... )
    """

    messages: List[Union[Message, Dict[str, Any]]] = Field(
        default_factory=list, description="Message history"
    )
    response_schema: Optional[ProviderSchema] = Field(
        default=None, description="Response validation schema"
    )

    model_config = ConfigDict(extra="allow")


class ControlCommand(BaseModel):
    """Control command for session management.

    API payload for controlling session execution (pause, resume, cancel, etc).

    Attributes:
        type: Command type (e.g., "pause", "resume", "cancel", "checkpoint").
        id: Optional identifier for checkpoint or control reference.

    Example:
        >>> cmd = ControlCommand(type="pause")
        >>> cmd2 = ControlCommand(type="checkpoint", id="cp_001")
    """

    type: str = Field(description="Control command type")
    id: Optional[str] = Field(default=None, description="Optional command-specific ID")


class Decision(BaseModel):
    """Final decision from LLM provider.

    Represents the LLM's complete decision including reasoning steps and chosen
    action. This is the canonical model for all provider decisions.

    Attributes:
        reasoning: List of reasoning steps explaining the decision.
        action: The chosen action type (RESPOND, TOOL_CALL, or MOVE).
        response: Set if action is RESPOND.
        tool_call: Set if action is TOOL_CALL.
        step_id: Set if action is MOVE (target node ID).

    Example:
        >>> d = Decision(
        ...     reasoning=["User asked for weather", "Can invoke get_weather tool"],
        ...     action="TOOL_CALL",
        ...     tool_call=ToolCall(tool_name="get_weather", tool_kwargs={})
        ... )
    """

    reasoning: List[str] = Field(description="Reasoning steps")
    action: Literal["RESPOND", "TOOL_CALL", "MOVE"] = Field(
        description="Chosen action type"
    )
    response: Optional[str] = Field(
        default=None, description="Response text (for RESPOND)"
    )
    tool_call: Optional[ToolCall] = Field(
        default=None, description="Tool call specification (for TOOL_CALL)"
    )
    step_id: Optional[str] = Field(
        default=None, description="Target node ID (for MOVE)"
    )


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
    "Decision",
]
