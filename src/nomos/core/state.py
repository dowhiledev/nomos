"""Session state projection models (skeleton)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from .events import SessionEvent
from .schemas import Checkpoint


class SessionState(BaseModel):
    session_id: str
    current_node: Optional[str] = None
    last_action: Optional[str] = None
    history_tail: List[SessionEvent] = Field(default_factory=list)
    flow_state: Optional[Dict[str, Any]] = None
    checkpoints: List[Checkpoint] = Field(default_factory=list)


__all__ = ["SessionState"]
