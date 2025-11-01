"""Minimal Agent/Graph spec (skeleton).

Keeps just enough structure to let the orchestrator track current node and apply routing.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel


class NodeSpec(BaseModel):
    id: str
    prompt: Optional[str] = None


class EdgeSpec(BaseModel):
    from_id: str
    to_id: str
    when: Optional[str] = None  # e.g., "MOVE:next"

    def matches(self, decision: dict) -> bool:  # noqa: ANN001
        action = decision.get("action")
        if action == "MOVE":
            step = decision.get("step_id")
            return self.when == f"MOVE:{step}"
        return False


class AgentSpec(BaseModel):
    name: str
    start: str
    nodes: List[NodeSpec]
    edges: List[EdgeSpec]

    def allowed_targets(self, current: str) -> List[str]:
        return [e.to_id for e in self.edges if e.from_id == current]

    def route(self, current: str, decision: dict) -> Optional[str]:  # noqa: ANN001
        for e in self.edges:
            if e.from_id != current:
                continue
            if e.matches(decision):
                return e.to_id
        return None

