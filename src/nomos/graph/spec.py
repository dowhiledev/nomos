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
    condition: Optional[str] = None  # natural-language condition for prompting


class AgentSpec(BaseModel):
    name: str
    start: str
    nodes: List[NodeSpec]
    edges: List[EdgeSpec]

    def allowed_targets(self, current: str) -> List[str]:
        return [e.to_id for e in self.edges if e.from_id == current]

    def route(self, current: str, decision: dict) -> Optional[str]:  # noqa: ANN001
        # Runtime routes solely based on the decision-provided step_id
        # and the set of allowed targets from the current node.
        if decision.get("action") == "MOVE":
            step = decision.get("step_id")
            return step if step in self.allowed_targets(current) else None
        return None

    def validate_spec(self) -> None:
        node_ids = {n.id for n in self.nodes}
        if self.start not in node_ids:
            raise ValueError(f"start node '{self.start}' not found in nodes")
        seen = set()
        for e in self.edges:
            if e.from_id not in node_ids:
                raise ValueError(f"edge.from_id '{e.from_id}' not found in nodes")
            if e.to_id not in node_ids:
                raise ValueError(f"edge.to_id '{e.to_id}' not found in nodes")
            key = (e.from_id, e.to_id, e.condition)
            if key in seen:
                raise ValueError(f"duplicate edge detected: {key}")
            seen.add(key)
        # reachability from start
        adj = {}
        for nid in node_ids:
            adj[nid] = []
        for e in self.edges:
            adj[e.from_id].append(e.to_id)
        visited = set()
        stack = [self.start]
        while stack:
            cur = stack.pop()
            if cur in visited:
                continue
            visited.add(cur)
            stack.extend(adj.get(cur, []))
        unreachable = sorted(list(node_ids - visited))
        if unreachable:
            raise ValueError(f"unreachable nodes: {', '.join(unreachable)}")


def compile_agent(spec: AgentSpec) -> AgentSpec:
    """Validate and return the spec (placeholder for future transforms)."""
    spec.validate_spec()
    return spec
