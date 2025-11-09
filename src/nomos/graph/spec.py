"""Agent specification and graph validation.

This module defines the core data structures for agent graphs:
- NodeSpec: A step in the agent's decision-making process
- EdgeSpec: A possible transition between nodes
- AgentSpec: The complete compiled graph specification

AgentSpec provides routing logic, validation, and introspection capabilities
used by the orchestrator to drive session execution through the graph.
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class NodeSpec(BaseModel):
    """Specification for a single node (step) in the agent graph.

    Represents a decision point or action node where the LLM receives instructions
    and makes decisions about the next step.

    Attributes:
        id: Unique node identifier within the graph.
        prompt: Natural language instruction for the LLM at this node.
            If not provided, uses defaults from AgentSpec or LLM provider.
        tools: List of tool names available at this node (optional).
            If not specified, all tools are potentially available.

    Example:
        >>> node = NodeSpec(
        ...     id="gather_requirements",
        ...     prompt="Ask the user about their requirements",
        ...     tools=["ask_clarifying_question"]
        ... )
    """

    id: str = Field(description="Unique node identifier")
    prompt: Optional[str] = Field(
        default=None, description="LLM instruction prompt for this node"
    )
    tools: Optional[List[str]] = Field(
        default=None, description="Available tool names at this node"
    )


class EdgeSpec(BaseModel):
    """Specification for a transition between nodes.

    Represents a possible routing from one node to another. The condition is
    a natural-language description shown to the LLM as a routing option.
    The runtime validates decisions against allowed targets only.

    Attributes:
        from_id: Source node ID.
        to_id: Target node ID.
        condition: Natural-language condition for this transition.
            Shown to the LLM to help it decide whether to take this edge.

    Example:
        >>> edge = EdgeSpec(
        ...     from_id="gather_requirements",
        ...     to_id="implement_solution",
        ...     condition="User has provided all requirements"
        ... )
    """

    from_id: str = Field(description="Source node ID")
    to_id: str = Field(description="Target node ID")
    condition: Optional[str] = Field(
        default=None, description="Natural-language routing condition"
    )


class AgentSpec(BaseModel):
    """Complete specification for an agent graph.

    The canonical specification that gets passed to the orchestrator. Includes
    all nodes and edges, plus methods for validation and routing logic.

    The orchestrator uses AgentSpec to:
    - Determine starting node
    - Apply routing decisions (validate MOVE targets)
    - Look up node-specific configuration and tools
    - Validate graph connectivity

    Attributes:
        name: Human-readable graph name for debugging.
        start: ID of the starting node.
        nodes: List of all NodeSpec definitions.
        edges: List of all EdgeSpec definitions.

    Example:
        >>> spec = AgentSpec(
        ...     name="support_agent",
        ...     start="greet",
        ...     nodes=[
        ...         NodeSpec(id="greet", prompt="Greet the user"),
        ...         NodeSpec(id="gather", prompt="Gather information"),
        ...     ],
        ...     edges=[
        ...         EdgeSpec(from_id="greet", to_id="gather", condition="..."),
        ...     ]
        ... )
        >>> spec.validate_spec()  # Raises if invalid
    """

    name: str = Field(description="Graph name")
    start: str = Field(description="Starting node ID")
    nodes: List[NodeSpec] = Field(description="Node specifications")
    edges: List[EdgeSpec] = Field(description="Edge specifications")

    def allowed_targets(self, current: str) -> List[str]:
        """Get valid routing targets from a node.

        Args:
            current: Current node ID.

        Returns:
            List of node IDs reachable via outgoing edges.
        """
        return [e.to_id for e in self.edges if e.from_id == current]

    def get_node_tools(self, node_id: str) -> List[str]:
        """Get tools available at a specific node.

        Args:
            node_id: Node identifier.

        Returns:
            List of tool names available at this node (empty if unrestricted).
        """
        for node in self.nodes:
            if node.id == node_id:
                return node.tools or []
        return []

    def route(self, current: str, decision: dict) -> Optional[str]:  # noqa: ANN001
        """Validate and apply a routing decision.

        Checks if a MOVE decision is valid (target in allowed_targets).
        Returns the target node ID if valid, None otherwise.

        Args:
            current: Current node ID.
            decision: Decision dict (typically with 'action' and 'step_id' keys).

        Returns:
            Target node ID if valid MOVE, None otherwise.
        """
        # Runtime routes solely based on the decision-provided step_id
        # and the set of allowed targets from the current node.
        if decision.get("action") == "MOVE":
            step = decision.get("step_id")
            return step if step in self.allowed_targets(current) else None
        return None

    def validate_spec(self) -> None:
        """Validate the graph specification for correctness.

        Checks:
        - Start node exists
        - All edge endpoints exist in nodes
        - No duplicate edges
        - All nodes are reachable from start (no orphaned nodes)

        Raises:
            ValueError: If validation fails with descriptive message.
        """
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
        adj: dict[str, list[str]] = {}
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
    """Compile an agent specification (validates and returns).

    Currently a pass-through that validates the spec.
    In future, could perform optimizations or transformations.

    Args:
        spec: AgentSpec to compile.

    Returns:
        The same spec (after validation).

    Raises:
        ValueError: If spec is invalid.
    """
    spec.validate_spec()
    return spec
