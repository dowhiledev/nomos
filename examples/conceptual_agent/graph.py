"""Conceptual graph composition for Nomos vNext example (user code).

Notes applied:
- Nodes/steps are the only vertices in the graph. Tools are not nodes; they are called by nodes (ReACT-style) and influence the node's decision.
- Edges connect nodes with conditions; cycles are allowed.
- Compiled graph returns an Agent.
- Nodes can reference another Agent as a tool (agent-agent communication).
- Global memory/LLM provider can be overridden per subgraph.
"""

from __future__ import annotations


from nomos.graph import Graph, LLMNode, Edge, as_tool  # provided by vNext
from nomos.core import Agent  # compiled output type

from .tools import db_query, web_search


def make_specialist_agent() -> Agent:
    """Specialist sub-agent with its own memory/LLM overrides.

    Tools are defined on the node; edges are between nodes only.
    Cycles allowed for iterative research.
    """
    sg = (
        Graph(name="specialist", llm="openai:gpt-4o", memory="flow")
        .add(
            LLMNode(
                id="specialist.research",
                prompt="Specialist research on narrow domain; gather relevant facts",
                tools=[web_search],  # tools called from within node
            ),
            LLMNode(
                id="specialist.summarize",
                prompt="Summarize findings concisely for parent agent",
            ),
        )
        .edge(
            Edge("specialist.research", "specialist.research", when="MOVE:iterate")
        )  # cycle
        .edge(
            Edge("specialist.research", "specialist.summarize", when="MOVE:summarize")
        )
        .compile()
    )
    # compile() returns an Agent (library behavior)
    return sg


def make_agent() -> Agent:
    """Main agent compiled from graph.

    Nodes call tools (including other agents-as-tools). Edges route between nodes.
    """
    specialist = make_specialist_agent()

    g = (
        Graph(name="travel_planner", llm="openai:gpt-4o-mini", memory="session")
        .add(
            LLMNode(
                id="intake",
                prompt="Collect destination, dates, budget, preferences; validate constraints",
            ),
            LLMNode(
                id="research",
                prompt="Use tools to research itinerary options and prices",
                llm="openai:gpt-4o-mini",  # node-level override
                tools=[
                    web_search,
                    db_query,
                    as_tool(specialist, name="specialist.helper"),  # agent-as-tool
                ],
            ),
            LLMNode(
                id="review",
                prompt="Review plan with the user; ask for corrections if needed",
            ),
            LLMNode(
                id="finalize",
                prompt="Produce final itinerary and costs; end session",
            ),
        )
        # edges between nodes (conditions based on node decisions)
        .edge(Edge("intake", "research", when="MOVE:research"))
        .edge(Edge("research", "research", when="MOVE:iterate"))  # loop while refining
        .edge(Edge("research", "review", when="MOVE:review"))
        .edge(Edge("review", "research", when="MOVE:revise"))  # cycle allowed
        .edge(Edge("review", "finalize", when="MOVE:finalize"))
        .compile()
    )

    return g


__all__ = ["make_agent", "make_specialist_agent"]
