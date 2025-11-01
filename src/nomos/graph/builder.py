"""Developer-first Graph builder DSL (minimal).

Example:
    gb = GraphBuilder(name="demo", start="start")
    (gb.node("start", prompt="Collect info")
       .node("work", prompt="Do work")
       .edge("start", "work", when="MOVE:work"))
    spec = gb.compile()
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field, PrivateAttr
from pydantic.config import ConfigDict

from .spec import AgentSpec, EdgeSpec, NodeSpec, compile_agent


class GraphBuilder(BaseModel):
    name: str
    start: str
    _nodes: List[NodeSpec] = PrivateAttr(default_factory=list)
    _edges: List[EdgeSpec] = PrivateAttr(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def node(self, id: str, *, prompt: Optional[str] = None) -> "GraphBuilder":  # noqa: A003
        self._nodes.append(NodeSpec(id=id, prompt=prompt))
        return self

    def edge(self, from_id: str, to_id: str, *, condition: Optional[str] = None) -> "GraphBuilder":
        self._edges.append(EdgeSpec(from_id=from_id, to_id=to_id, condition=condition))
        return self

    def compile(self) -> AgentSpec:
        spec = AgentSpec(name=self.name, start=self.start, nodes=list(self._nodes), edges=list(self._edges))
        return compile_agent(spec)


__all__ = ["GraphBuilder"]
