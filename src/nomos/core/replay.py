"""Replay and state projection utilities for event-sourced sessions.

This module provides utilities for reconstructing session state from events.
State projection enables:
- Debugging and introspection of session execution
- Deterministic reconstruction at any point in time
- Timeline visualization and analysis
- Session resumption after interruption
"""

from __future__ import annotations

from typing import Any, Dict, List

from .events import EventType, SessionEvent
from .state import SessionState


def project_state(session_id: str, events: List[SessionEvent]) -> Dict[str, Any]:  # noqa: ANN401
    """Project session state from a list of events.

    Scans events in order and reconstructs the session state at that point.
    This enables deterministic replay: feeding the same events through projection
    always yields the same state.

    The function tracks:
    - Current node from ROUTING_APPLIED events
    - Last action type
    - Recent event history (tail of last 50 events)

    Args:
        session_id: The session ID being projected.
        events: List of SessionEvent objects in order.

    Returns:
        Dictionary representation of SessionState at the end of the event list.
        Use SessionState.model_validate() to get a typed object if needed.

    Example:
        >>> events = await store.read_by_session(session_id)
        >>> state_dict = project_state(session_id, events)
        >>> print(f"Node: {state_dict['current_node']}")
        >>> print(f"Last action: {state_dict['last_action']}")
    """
    state = SessionState(session_id=session_id)
    tail = []
    for ev in events[-50:]:
        tail.append(ev)
        if ev.type == EventType.DECISION_COMPLETED:
            state.last_action = "decision.completed"
        if ev.type == EventType.TOKEN_EMITTED:
            state.last_action = "io.token"
        if ev.type == EventType.ROUTING_APPLIED:
            state.current_node = ev.data.get("to")
        if ev.type == EventType.CHECKPOINT_RESTORED:
            state.current_node = ev.data.get("node_id")
    state.history_tail = tail
    return state.model_dump()


__all__ = ["project_state"]
