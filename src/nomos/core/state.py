"""Session state projection models.

This module defines the SessionState model which represents a materialized
(projected) view of a session at a point in time. State is computed from the
event log, enabling deterministic replay and state reconstruction.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .events import SessionEvent
from .schemas import Checkpoint


class SessionState(BaseModel):
    """Materialized state snapshot for a session.

    Represents the current state of a session as computed from its event log.
    This model serves as the basis for:
    - Session introspection via REST APIs
    - State-based decision logic
    - Checkpointing for interruption/resume
    - Timeline visualization and debugging

    State is typically projected via the replay.project_state() function which
    scans the event log and updates this model based on event types.

    Attributes:
        session_id: Unique session identifier.
        current_node: ID of the node the session is currently in (or None).
        last_action: Type of the last action taken (e.g., "decision.completed").
        history_tail: Recent events (typically last 50) for context.
        messages: Conversation message history.
        flow_state: Arbitrary application state (node-specific context).
        checkpoints: List of saved checkpoints for this session.

    Example:
        >>> state = project_state(session_id, events)
        >>> print(f"Session {state.session_id} at node {state.current_node}")
        >>> print(f"Last action: {state.last_action}")
    """

    session_id: str = Field(description="Unique session identifier")
    current_node: Optional[str] = Field(
        default=None, description="Current node in the graph"
    )
    last_action: Optional[str] = Field(default=None, description="Type of last action")
    history_tail: List[SessionEvent] = Field(
        default_factory=list, description="Recent events for context"
    )
    messages: List[Dict[str, Any]] = Field(
        default_factory=list, description="Conversation history"
    )
    flow_state: Optional[Dict[str, Any]] = Field(
        default=None, description="Application-specific state"
    )
    checkpoints: List[Checkpoint] = Field(
        default_factory=list, description="Saved checkpoints for this session"
    )


__all__ = ["SessionState"]
