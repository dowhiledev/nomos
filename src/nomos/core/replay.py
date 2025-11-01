"""Replay utilities for projecting state from events."""

from __future__ import annotations

from typing import Any, Dict, List

from .events import EventType, SessionEvent
from .state import SessionState


def project_state(session_id: str, events: List[SessionEvent]) -> Dict[str, Any]:  # noqa: ANN401
    state = SessionState(session_id=session_id)
    tail = []
    for ev in events[-50:]:
        tail.append(ev)
        if ev.type == EventType.DECISION_COMPLETED.value:
            state.last_action = "decision.completed"
        if ev.type == EventType.TOKEN_EMITTED.value:
            state.last_action = "io.token"
        if ev.type == EventType.ROUTING_APPLIED.value:
            state.current_node = ev.data.get("to")
        if ev.type == EventType.CHECKPOINT_RESTORED.value:
            state.current_node = ev.data.get("node_id")
    state.history_tail = tail
    return state.model_dump()


__all__ = ["project_state"]
