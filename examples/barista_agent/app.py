from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import Graph, LLMNode, Edge
from nomos.tools.runner import SimpleToolRunner


# In-memory state (demo only)
_cart: list[dict] = []


# Tools inspired by .old barista_tools.py
async def get_available_coffee_options():
    await asyncio.sleep(0)
    opts = [
        {"type": "Espresso", "sizes": ["S", "M", "L"], "prices": [2.5, 3.0, 3.5]},
        {"type": "Latte", "sizes": ["S", "M", "L"], "prices": [3.0, 3.5, 4.0]},
    ]
    yield {"type": "tool.completed", "result": opts}


async def add_to_cart(coffee_type: str, size: str, price: float):
    _cart.append({"coffee_type": coffee_type, "size": size, "price": price})
    await asyncio.sleep(0)
    yield {"type": "tool.completed", "result": {"ok": True, "count": len(_cart)}}


async def get_order_summary():
    total = sum(i["price"] for i in _cart)
    await asyncio.sleep(0)
    yield {"type": "tool.completed", "result": {"items": list(_cart), "total": total}}


async def clear_cart():
    _cart.clear()
    await asyncio.sleep(0)
    yield {"type": "tool.completed", "result": {"ok": True}}


async def finalize_order(payment_method: str, payment: float | None = None):
    yield {"type": "tool.progress", "stage": "process_payment"}
    await asyncio.sleep(0.1)
    total = sum(i["price"] for i in _cart)
    yield {"type": "tool.stdout", "line": f"total: {total}"}
    await asyncio.sleep(0.1)
    change = (payment or 0) - total if payment_method == "Cash" else 0
    _cart.clear()
    yield {"type": "tool.completed", "result": {"ok": True, "change": change}}


class BaristaProvider:
    def __init__(self) -> None:
        self._turn = 0

    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Stream a small token to demonstrate streaming UX
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "… "},
        }
        # Turn 0: move to order_entry; Turn 1: call add_to_cart; Turn 2: move to order_review; Turn 3: call finalize_order; Turn 4: move to order_completed
        flow = [
            {"action": "MOVE", "step_id": "order_entry"},
            {
                "action": "TOOL_CALL",
                "tool_call": {
                    "tool_name": "add.to.cart",
                    "tool_kwargs": {"coffee_type": "Latte", "size": "M", "price": 3.5},
                },
            },
            {"action": "MOVE", "step_id": "order_review"},
            {
                "action": "TOOL_CALL",
                "tool_call": {
                    "tool_name": "finalize.order",
                    "tool_kwargs": {"payment_method": "Card"},
                },
            },
            {"action": "MOVE", "step_id": "order_completed"},
        ]
        idx = min(self._turn, len(flow) - 1)
        self._turn += 1
        yield {"type": EventType.DECISION_COMPLETED.value, "data": flow[idx]}


async def main() -> None:
    g = (
        Graph(name="barista")
        .add(
            LLMNode(
                id="greeting", prompt="Greet and offer menu", tools=["get.options"]
            ),
            LLMNode(
                id="order_entry",
                prompt="Collect preference and size; update cart",
                tools=["get.options", "add.to.cart", "clear.cart"],
            ),
            LLMNode(
                id="order_review",
                prompt="Review order and total",
                tools=["get.summary"],
            ),
            LLMNode(
                id="payment_processing",
                prompt="Process payment",
                tools=["finalize.order"],
            ),
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

    tools = {
        "get.options": get_available_coffee_options,
        "add.to.cart": add_to_cart,
        "get.summary": get_order_summary,
        "clear.cart": clear_cart,
        "finalize.order": finalize_order,
    }
    runner = SimpleToolRunner(tools)
    # derive per-node allowed tools from node.tools and apply via node_overrides
    node_overrides: Dict[str, Dict[str, Any]] = {}
    for node in g._nodes:  # accessing runtime graph nodes for example purposes
        allowed = {t for t in (node.tools or []) if isinstance(t, str) and t in tools}
        if allowed:
            node_overrides[node.id] = {"allowed_tools": allowed}
    orch = Orchestrator(
        agent=spec,
        provider=BaristaProvider(),
        tool_runner=runner,
        node_overrides=node_overrides,
    )
    s = await orch.create_session()

    async def wait_for_event(inputs: Dict[str, Any], pred, timeout: float = 5.0):  # noqa: ANN401
        async def _consume():
            async for ev in orch.stream(session_id=s.id, inputs=inputs):
                if pred(ev):
                    return ev
        try:
            return await asyncio.wait_for(_consume(), timeout=timeout)
        except asyncio.TimeoutError:
            print("[warn] timed out waiting for event", flush=True)  # noqa: T201
            return None

    # 1) Greet -> order_entry
    ev = await wait_for_event(
        {"messages": [{"role": "user", "content": [{"type": "text", "data": "hello"}]}]},
        lambda e: e["type"] == EventType.ROUTING_APPLIED.value,
    )
    if ev:
        print("route:", ev["data"])  # noqa: T201

    # 2) Tool add_to_cart at order_entry
    await wait_for_event(
        {"messages": [{"role": "user", "content": [{"type": "text", "data": "I want a latte"}]}]},
        lambda e: e["type"] in ("tool.completed", "tool.error"),
    )

    # 3) order_entry -> order_review
    ev = await wait_for_event(
        {"messages": [{"role": "user", "content": [{"type": "text", "data": "review"}]}]},
        lambda e: e["type"] == EventType.ROUTING_APPLIED.value,
    )
    if ev:
        print("route:", ev["data"])  # noqa: T201

    # 4) finalize_order tool
    await wait_for_event(
        {"messages": [{"role": "user", "content": [{"type": "text", "data": "pay"}]}]},
        lambda e: e["type"] in ("tool.completed", "tool.error"),
    )

    # 5) payment_processing -> order_completed
    ev = await wait_for_event(
        {"messages": [{"role": "user", "content": [{"type": "text", "data": "done"}]}]},
        lambda e: e["type"] == EventType.ROUTING_APPLIED.value,
    )
    if ev:
        print("route:", ev["data"])  # noqa: T201


if __name__ == "__main__":
    asyncio.run(main())
