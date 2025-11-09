"""Developer-first Graph builder DSL for programmatic agent definition.

This module provides a fluent, chainable API for constructing agent graphs.
The GraphBuilder makes it easy to define nodes and edges in Python without
external configuration files.

Example:
    >>> gb = GraphBuilder(name="my_agent", start="start")
    >>> (gb
    ...     .node("start", prompt="Start the conversation")
    ...     .node("work", prompt="Do the work")
    ...     .edge("start", "work", condition="Start completed"))
    >>> spec = gb.compile()
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, PrivateAttr, Field
from pydantic.config import ConfigDict

from .spec import AgentSpec, EdgeSpec, NodeSpec, compile_agent


class GraphBuilder(BaseModel):
    """Fluent builder for constructing agent graphs.

    Provides a chainable API for defining nodes and edges, then compiling
    to an AgentSpec for use with the orchestrator.

    Example:
        >>> builder = GraphBuilder(name="assistant", start="greeting")
        >>> builder.node("greeting", prompt="Greet the user")
        >>> builder.node("help", prompt="Help the user")
        >>> builder.edge("greeting", "help", condition="User needs help")
        >>> spec = builder.compile()

    Attributes:
        name: Human-readable graph name.
        start: ID of the starting node.
    """

    name: str = Field(description="Graph name")
    start: str = Field(description="Starting node ID")
    _nodes: List[NodeSpec] = PrivateAttr(default_factory=list)
    _edges: List[EdgeSpec] = PrivateAttr(default_factory=list)

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def node(self, id: str, *, prompt: Optional[str] = None) -> "GraphBuilder":  # noqa: A003
        """Add a node to the graph.

        Nodes are decision points where the LLM receives instructions and
        determines the next action (respond, call tool, or move to next node).

        Args:
            id: Unique node identifier within the graph.
            prompt: Optional LLM instruction for this node. Can be overridden
                at runtime or in the orchestrator.

        Returns:
            Self for method chaining.

        Example:
            >>> builder.node("gather", prompt="Gather user information")
            >>> builder.node("respond", prompt="Generate response")
        """
        self._nodes.append(NodeSpec(id=id, prompt=prompt))
        return self

    def edge(
        self, from_id: str, to_id: str, *, condition: Optional[str] = None
    ) -> "GraphBuilder":
        """Add an edge (transition) between nodes.

        Edges define routing possibilities. The condition is shown to the LLM
        as a natural-language option when deciding whether to use this edge.

        Args:
            from_id: Source node ID.
            to_id: Target node ID.
            condition: Optional natural-language condition explaining when
                this edge should be taken (shown to LLM).

        Returns:
            Self for method chaining.

        Example:
            >>> builder.edge("gather", "respond", condition="All info collected")
            >>> builder.edge("gather", "clarify", condition="Need more info")
        """
        self._edges.append(EdgeSpec(from_id=from_id, to_id=to_id, condition=condition))
        return self

    def compile(self) -> AgentSpec:
        """Compile the graph into an AgentSpec.

        Validates the graph (reachability, no orphans, etc) and returns
        a compiled AgentSpec ready for the orchestrator.

        Returns:
            Compiled AgentSpec.

        Raises:
            ValueError: If the graph is invalid (e.g., start node missing,
                unreachable nodes, duplicate edges).

        Example:
            >>> builder = GraphBuilder(name="bot", start="greet")
            >>> builder.node("greet").node("end")
            >>> builder.edge("greet", "end")
            >>> spec = builder.compile()
        """
        spec = AgentSpec(
            name=self.name,
            start=self.start,
            nodes=list(self._nodes),
            edges=list(self._edges),
        )
        return compile_agent(spec)


__all__ = ["GraphBuilder"]
