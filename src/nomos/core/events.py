"""Domain events and basic types (skeleton).

Minimal canonical envelope for SessionEvent and a small set of common event types.
These are intentionally lightweight for Milestone 1 and will evolve alongside .ddd/DOMAIN_EVENTS.md.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional
from typing_extensions import Literal

from pydantic import BaseModel, Field


class EventType(str, Enum):
    SESSION_CREATED = "session.created"
    INPUT_ENQUEUED = "input.enqueued"
    DECISION_STARTED = "decision.started"
    TOKEN_EMITTED = "io.token"
    DECISION_COMPLETED = "decision.completed"
    ROUTING_APPLIED = "routing.applied"
    CONTROL_APPLIED = "control.applied"
    CANCEL_APPLIED = "cancel.applied"
    CHECKPOINT_CREATED = "checkpoint.created"
    CHECKPOINT_RESTORED = "checkpoint.restored"
    ERROR_OCCURRED = "error.occurred"
    # Tool execution frames
    TOOL_STARTED = "tool.started"
    TOOL_PROGRESS = "tool.progress"
    TOOL_STDOUT = "tool.stdout"
    TOOL_COMPLETED = "tool.completed"
    TOOL_ERROR = "tool.error"


class SessionEvent(BaseModel):
    """Canonical session event (append-only).

    All event types are defined in the EventType enum, including:
    - Core orchestration events (SESSION_CREATED, DECISION_COMPLETED, etc.)
    - Tool execution frames (TOOL_STARTED, TOOL_PROGRESS, TOOL_COMPLETED, TOOL_ERROR)
    """

    session_id: str
    type: EventType
    data: Dict[str, Any] = Field(default_factory=dict)
    node_id: Optional[str] = None
    event_id: Optional[str] = None


class TokenFrame(BaseModel):
    """Typed frame for token streaming from provider adapters."""

    type: Literal["io.token"] = "io.token"
    data: Dict[str, Any]


class DecisionFrame(BaseModel):
    """Typed frame for final provider decisions (RESPOND or TOOL_CALL)."""

    type: Literal["decision.completed"] = "decision.completed"
    data: Dict[str, Any]


__all__ = ["EventType", "SessionEvent", "TokenFrame", "DecisionFrame"]
