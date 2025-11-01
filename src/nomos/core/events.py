"""Domain events and basic types (skeleton).

Minimal canonical envelope for SessionEvent and a small set of common event types.
These are intentionally lightweight for Milestone 1 and will evolve alongside .ddd/DOMAIN_EVENTS.md.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Optional

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


class SessionEvent(BaseModel):
    """Canonical session event (append-only)."""

    session_id: str
    type: str
    data: Dict[str, Any] = Field(default_factory=dict)
    node_id: Optional[str] = None
    event_id: Optional[str] = None


__all__ = ["EventType", "SessionEvent"]
