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
        if not self.when:
            return False
        # MOVE:<step_id>
        if action == "MOVE" and self.when.startswith("MOVE:"):
            step = decision.get("step_id")
            return self.when == f"MOVE:{step}"
        # RESPOND (wildcard)
        if action == "RESPOND" and self.when.startswith("RESPOND"):
            # RESPOND with optional tag: RESPOND:<tag>
            if self.when == "RESPOND":
                return True
            # match RESPOND:<tag> against decision tag or response_tag
            try_tag = None
            for key in ("tag", "response_tag"):
                if key in decision:
                    try_tag = decision.get(key)
                    break
            if try_tag is None:
                return False
            return self.when == f"RESPOND:{try_tag}"
        # END (wildcard)
        if action == "END" and self.when == "END":
            return True
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
            key = (e.from_id, e.to_id, e.when)
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
