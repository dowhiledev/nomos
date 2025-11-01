from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel
from pydantic.config import ConfigDict

from .spec import AgentSpec, NodeSpec, EdgeSpec, compile_agent


class LLMNode(BaseModel):
    id: str
    prompt: Optional[str] = None
    llm: Optional[str] = None
    tools: Optional[List[object]] = None  # user-provided callables (decorated or plain)
    memory: Optional[str] = None


class Edge(BaseModel):
    from_id: str
    to_id: str
    when: Optional[str] = None


class Graph(BaseModel):
    name: str
    llm: Optional[str] = None
    memory: Optional[str] = None
    _nodes: List[LLMNode] = []  # type: ignore[var-annotated]
    _edges: List[Edge] = []  # type: ignore[var-annotated]
    _start: Optional[str] = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def add(self, *nodes: LLMNode) -> "Graph":
        for n in nodes:
            if self._start is None:
                self._start = n.id
            self._nodes.append(n)
        return self

    def edge(self, e: Edge) -> "Graph":
        self._edges.append(e)
        return self

    def compile(self) -> AgentSpec:
        if not self._start:
            raise ValueError("graph has no start node; add at least one node")
        spec = AgentSpec(
            name=self.name,
            start=self._start,
            nodes=[NodeSpec(id=n.id, prompt=n.prompt) for n in self._nodes],
            edges=[
                EdgeSpec(from_id=e.from_id, to_id=e.to_id, condition=e.when)
                for e in self._edges
            ],
        )
        return compile_agent(spec)


__all__ = ["Graph", "LLMNode", "Edge"]
