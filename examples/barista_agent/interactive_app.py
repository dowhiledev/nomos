from __future__ import annotations

import asyncio
import os
from typing import Any, Dict
import json

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import Graph, LLMNode, Edge
from nomos.tools.runner import SimpleToolRunner
from nomos.llms.openai_provider import OpenAIProvider


async def main() -> None:
    # Graph with natural-language edge conditions and node-level tools
    g = (
        Graph(name="barista")
        .add(
            LLMNode(id="greeting", prompt="Greet and offer menu", tools=["get.options"]),
            LLMNode(
                id="order_entry",
                prompt="Collect preference and size; update cart",
                tools=["get.options", "add.to.cart", "clear.cart"],
            ),
            LLMNode(id="order_review", prompt="Review order and total", tools=["get.summary"]),
            LLMNode(id="payment_processing", prompt="Process payment", tools=["finalize.order"]),
            LLMNode(id="order_completed", prompt="Thank customer"),
            LLMNode(id="order_cancelled", prompt="Cancel order", tools=["clear.cart"]),
            LLMNode(id="session_end", prompt="End session", tools=["clear.cart"]),
        )
        .edge(
            Edge(
                from_id="greeting",
                to_id="order_entry",
                when="Customer is ready to place an order or browse menu",
            )
        )
    )
    g.edge(
        Edge(
            from_id="order_entry",
            to_id="order_review",
            when="Customer wants to review order or proceed to checkout",
        )
    )
    g.edge(
        Edge(
            from_id="order_review",
            to_id="payment_processing",
            when="Customer confirms order and wants to pay",
        )
    )
    g.edge(
        Edge(
            from_id="payment_processing",
            to_id="order_completed",
            when="Payment processed successfully",
        )
    )
    g.edge(
        Edge(
            from_id="order_review",
            to_id="order_cancelled",
            when="Customer wants to cancel the order",
        )
    )
    g.edge(
        Edge(
            from_id="order_completed",
            to_id="session_end",
            when="Customer is done and wants to leave",
        )
    )
    spec = g.compile()

    # Demo tools
    import examples.barista_agent.app as tools_mod  # reuse tool fns in app.py

    tools = {
        "get.options": tools_mod.get_available_coffee_options,
        "add.to.cart": tools_mod.add_to_cart,
        "get.summary": tools_mod.get_order_summary,
        "clear.cart": tools_mod.clear_cart,
        "finalize.order": tools_mod.finalize_order,
    }
    runner = SimpleToolRunner(tools)

    # derive per-node allowed tools from node.tools and apply via node_overrides
    node_overrides: Dict[str, Dict[str, Any]] = {}
    for node in g._nodes:  # accessing runtime graph nodes for example purposes
        allowed = {t for t in (node.tools or []) if isinstance(t, str) and t in tools}
        if allowed:
            node_overrides[node.id] = {"allowed_tools": allowed}

    provider = OpenAIProvider() if os.getenv("OPENAI_API_KEY") else tools_mod.BaristaProvider()
    orch = Orchestrator(agent=spec, provider=provider, tool_runner=runner, node_overrides=node_overrides)
    s = await orch.create_session()

    print("Welcome to Barista (vNext). Type /quit, /pause, /resume, /cancel.")  # noqa: T201

    async def receiver():
        async for ev in orch.stream(session_id=s.id):
            t = ev.get("type")
            if t == EventType.TOKEN_EMITTED.value:
                print(ev["data"].get("delta"), end="", flush=True)  # noqa: T201
            elif t == EventType.DECISION_COMPLETED.value:
                print("\n[decision]", ev.get("data"))  # noqa: T201
            elif t and t.startswith("tool."):
                print("\n", ev)  # noqa: T201
                # After a tool completes, feed a tool result message to drive the next turn
                if ev.get("type") == "tool.completed":
                    result = ev.get("result") or ev.get("data", {}).get("result")
                    tool_name = ev.get("tool") or "tool"
                    await orch.input(
                        session_id=s.id,
                        inputs={
                            "messages": [
                                {
                                    "role": "assistant",
                                    "content": [
                                        {
                                            "type": "text",
                                            "data": f"TOOL_RESULT {tool_name}: "
                                            + (json.dumps(result)[:1000] if result is not None else "done"),
                                        }
                                    ],
                                }
                            ]
                        },
                    )
            elif t == EventType.ROUTING_APPLIED.value:
                print("\n[route]", ev.get("data"))  # noqa: T201
                # Nudge the loop to continue at the new node
                await orch.input(session_id=s.id, inputs={"messages": []})

    async def sender():
        while True:
            line = await asyncio.to_thread(input, "You: ")
            line = line.strip()
            if not line:
                continue
            if line == "/quit":
                break
            if line == "/pause":
                await orch.control(session_id=s.id, command={"type": "pause.requested"})
                continue
            if line == "/resume":
                await orch.control(session_id=s.id, command={"type": "resume.requested"})
                continue
            if line == "/cancel":
                await orch.control(session_id=s.id, command={"type": "cancel.requested"})
                continue
            await orch.input(
                session_id=s.id,
                inputs={
                    "messages": [
                        {"role": "user", "content": [{"type": "text", "data": line}]}
                    ]
                },
            )

    await asyncio.gather(receiver(), sender())


if __name__ == "__main__":
    asyncio.run(main())
