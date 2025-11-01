"""Nomos vNext Barista Example - Interactive Coffee Ordering Agent

This example demonstrates a conversational agent that helps customers order coffee.
It uses a graph-based workflow with OpenAI for natural language understanding.
"""

import asyncio
from typing import Any, Dict

from dotenv import load_dotenv

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import Graph, LLMNode, Edge
from nomos.tools.runner import SimpleToolRunner
from nomos.llms.openai_provider import OpenAIProvider

# Load environment variables
load_dotenv()

# In-memory state (demo only)
_cart: list[dict] = []

# Create tool runner
runner = SimpleToolRunner()

# Tools
@runner.tool("get.options")
async def get_available_coffee_options():
    """Get available coffee options."""
    await asyncio.sleep(0)
    opts = [
        {"type": "Espresso", "sizes": ["S", "M", "L"], "prices": [2.5, 3.0, 3.5]},
        {"type": "Latte", "sizes": ["S", "M", "L"], "prices": [3.0, 3.5, 4.0]},
    ]
    return opts


@runner.tool("add.to.cart")
async def add_to_cart(coffee_type: str, size: str, price: float):
    """Add coffee to cart."""
    _cart.append({"coffee_type": coffee_type, "size": size, "price": price})
    await asyncio.sleep(0)
    return {"ok": True, "count": len(_cart)}


@runner.tool("get.summary")
async def get_order_summary():
    """Get order summary."""
    total = sum(i["price"] for i in _cart)
    await asyncio.sleep(0)
    return {"items": list(_cart), "total": total}


@runner.tool("clear.cart")
async def clear_cart():
    """Clear the cart."""
    _cart.clear()
    await asyncio.sleep(0)
    return {"ok": True}


@runner.tool("finalize.order", timeout=5)
def finalize_order(payment_method: str, payment: float | None = None):
    """Finalizes the Order."""
    total = sum(i["price"] for i in _cart)
    change = (payment or 0) - total if payment_method == "Cash" else 0
    _cart.clear()
    return {
        "result": {"ok": True, "change": change},
        "progress": ["process_payment"],
        "stdout": [f"total: {total}"]
    }


async def main() -> None:
    # Define the graph
    g = (
        Graph(name="barista")
        .add(
            LLMNode(
                id="greeting",
                prompt="Greet the customer warmly and ask how you can help them today. Use the get.options tool to get familiar with available options.",
                tools=["get.options"],
            ),
            LLMNode(
                id="order_entry",
                prompt="Help the customer build their order. Ask for coffee preference and size. Use get.options to check availability. Use add.to.cart when customer confirms.",
                tools=["get.options", "add.to.cart", "clear.cart"],
            ),
            LLMNode(
                id="order_review",
                prompt="Review the order and total using get.summary. Ask if ready to pay.",
                tools=["get.summary"],
            ),
            LLMNode(
                id="payment_processing",
                prompt="Process payment using finalize.order.",
                tools=["finalize.order"],
            ),
            LLMNode(id="order_completed", prompt="Thank the customer and end session."),
            LLMNode(
                id="order_cancelled",
                prompt="Cancel order and clear cart.",
                tools=["clear.cart"],
            ),
            LLMNode(id="session_end", prompt="End session.", tools=["clear.cart"]),
        )
        .edge(
            Edge(
                from_id="greeting",
                to_id="order_entry",
                when="Customer wants to place an order",
            )
        )
        .edge(
            Edge(
                from_id="order_entry",
                to_id="order_review",
                when="Customer wants to review order",
            )
        )
        .edge(
            Edge(
                from_id="order_review",
                to_id="payment_processing",
                when="Customer confirms payment",
            )
        )
        .edge(
            Edge(
                from_id="payment_processing",
                to_id="order_completed",
                when="Payment processed successfully",
            )
        )
        .edge(
            Edge(
                from_id="order_review",
                to_id="order_cancelled",
                when="Customer wants to cancel",
            )
        )
        .edge(
            Edge(
                from_id="order_completed",
                to_id="session_end",
                when="Session complete",
            )
        )
    )

    spec = g.compile()

    # Node overrides for allowed tools
    node_overrides: Dict[str, Dict[str, Any]] = {}
    for node in g._nodes:
        allowed = {t for t in (node.tools or []) if isinstance(t, str) and t in runner._registry}
        if allowed:
            node_overrides[node.id] = {"allowed_tools": allowed}

    # Use OpenAI provider
    provider = OpenAIProvider()
    orch = Orchestrator(
        agent=spec, provider=provider, tool_runner=runner, node_overrides=node_overrides
    )
    s = await orch.create_session()

    print("Welcome to Nomos Barista! Type /quit to exit, /pause, /resume, /cancel.")

    # Start with initial decision at greeting
    await orch.input(session_id=s.id, inputs={"messages": []})

    # Process initial greeting
    async for ev in orch.stream(session_id=s.id):
        t = ev.get("type")
        if t == EventType.TOKEN_EMITTED.value:
            print(ev["data"].get("delta"), end="", flush=True)
        elif t == EventType.DECISION_COMPLETED.value:
            data = ev.get("data", {})
            if data.get("action") == "RESPOND":
                print(f"\n[response] {data.get('response', '')}")
            else:
                print(f"\n[decision] {data}")
            break
        elif t and t.startswith("tool."):
            print(f"\n{ev}")
            if ev.get("type") == "tool.completed":
                result = ev.get("result")
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
                                        + (
                                            str(result)[:1000]
                                            if result is not None
                                            else "done"
                                        ),
                                    }
                                ],
                            }
                        ]
                    },
                )
        elif t == EventType.ROUTING_APPLIED.value:
            print(f"\n[route] {ev.get('data')}")
            await orch.input(session_id=s.id, inputs={"messages": []})

    while True:
        try:
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
                await orch.control(
                    session_id=s.id, command={"type": "resume.requested"}
                )
                continue
            if line == "/cancel":
                await orch.control(
                    session_id=s.id, command={"type": "cancel.requested"}
                )
                continue

            # Send user input
            await orch.input(
                session_id=s.id,
                inputs={
                    "messages": [
                        {"role": "user", "content": [{"type": "text", "data": line}]}
                    ]
                },
            )

            # Process the response turn
            async for ev in orch.stream(session_id=s.id):
                t = ev.get("type")
                if t == EventType.TOKEN_EMITTED.value:
                    print(ev["data"].get("delta"), end="", flush=True)
                elif t == EventType.DECISION_COMPLETED.value:
                    data = ev.get("data", {})
                    if data.get("action") == "RESPOND":
                        print(f"\n[response] {data.get('response', '')}")
                    else:
                        print(f"\n[decision] {data}")
                    # Decision completed, turn is done
                    break
                elif t and t.startswith("tool."):
                    print(f"\n{ev}")
                    # After a tool completes, feed a tool result message to drive the next turn
                    if ev.get("type") == "tool.completed":
                        result = ev.get("result")
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
                                                + (
                                                    str(result)[:1000]
                                                    if result is not None
                                                    else "done"
                                                ),
                                            }
                                        ],
                                    }
                                ]
                            },
                        )
                elif t == EventType.ROUTING_APPLIED.value:
                    print(f"\n[route] {ev.get('data')}")
                    # Nudge the loop to continue at the new node
                    await orch.input(session_id=s.id, inputs={"messages": []})
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    asyncio.run(main())
