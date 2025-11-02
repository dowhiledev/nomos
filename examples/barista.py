"""Nomos vNext Barista Example - Interactive Coffee Ordering Agent

This example demonstrates a conversational agent that helps customers order coffee.
It uses a graph-based workflow with OpenAI for natural language understanding.
"""

import asyncio
from typing import Any, Dict, Literal, Optional
import uuid

from dotenv import load_dotenv

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import Graph, Step, Transition
from nomos.tools.runner import SimpleToolRunner
from nomos.llms.openai import OpenAI

# Load environment variables
load_dotenv()

# In-memory state (demo only)
_cart: list[dict] = []
_sales: list[dict] = []

# Create tool runner
runner = SimpleToolRunner()


# Tools
@runner.tool("get.options")
async def get_available_coffee_options():
    """
    Get available coffee options, sizes, and prices.
    """
    coffee_options = [
        {
            "type": "Espresso",
            "sizes": ["Small", "Medium", "Large"],
            "prices": [2.5, 3.0, 3.5],
        },
        {
            "type": "Latte",
            "sizes": ["Small", "Medium", "Large"],
            "prices": [3.0, 3.5, 4.0],
        },
        {
            "type": "Cappuccino",
            "sizes": ["Small", "Medium", "Large"],
            "prices": [3.0, 3.5, 4.0],
        },
    ]
    return f"Available coffee options: {coffee_options}"


def get_total_price() -> float:
    """
    Calculate the total price of all orders in the cart.
    """
    total_price = sum(item["price"] for item in _cart)
    return total_price


@runner.tool("add.to.cart")
def add_to_cart(coffee_type: str, size: str, price: float) -> str:
    """
    Add a coffee item to the cart.
    """
    global _cart
    item_id = str(uuid.uuid4())
    _cart.append(
        {
            "item_id": item_id,
            "coffee_type": coffee_type,
            "size": size,
            "price": price,
        }
    )
    current_total = get_total_price()
    return f"Item {item_id} added to cart. Current total: ${current_total:.2f}"


@runner.tool("remove.item")
def remove_item(item_id: str) -> str:
    """
    Remove an item from the cart.
    """
    global _cart
    _cart = [item for item in _cart if item["item_id"] != item_id]
    return f"Item {item_id} removed successfully."


@runner.tool("get.summary")
async def get_order_summary() -> str:
    """
    Get a summary of all items in the cart.
    """
    if not _cart:
        return "No Items in the cart."
    summary = "\n".join(
        f"Item ID: {item['item_id']}, Coffee: {item['coffee_type']}, Size: {item['size']}, Price: ${item['price']:.2f}"
        for item in _cart
    )
    await asyncio.sleep(0.5)
    return f"Order Summary:\n{summary}\nTotal Price: ${get_total_price():.2f}"


@runner.tool("clear.cart")
def clear_cart() -> str:
    """
    Clear all items from the cart.
    """
    global _cart
    _cart = []
    return "All items cleared successfully."


@runner.tool("finalize.order", timeout=5)
async def finalize_order(
    payment_method: Literal["Card", "Cash"], payment: Optional[float] = None
) -> str:
    """
    Finalize the order and clear the cart.
    """
    global _cart, _sales
    if not _cart:
        return "No orders to finalize."
    total_price = get_total_price()
    balance = payment - total_price if (payment and payment_method == "Cash") else None
    if balance < 0:
        return (
            f"Insufficient payment amount for the order. Requires ${-balance:.2f} more."
        )
    _sales.append(
        {
            "order_id": str(uuid.uuid4()),
            "total_price": total_price,
            "payment_method": payment_method,
            "payment": payment,
            "balance": payment - total_price if payment else None,
            "items": _cart.copy(),
        }
    )
    clear_cart()
    if balance is not None or balance > 0:
        return (
            f"Order finalized! Total price: ${total_price:.2f}. "
            f"Payment method: {payment_method}. Change: ${balance:.2f}. Thank you for your order!"
        )
    return (
        f"Order finalized! Total price: ${total_price:.2f}. Thank you for your order!"
    )


async def main() -> None:
    # Define the graph
    g = (
        Graph(name="barista")
        .add(
            Step(
                id="greeting",
                prompt=(
                    "Greet the customer warmly and ask how you can help them today. "
                    "Use the `get.options` tool to get familiar with available options. "
                    "If the customer mentions a specific coffee preference, check if it's available. "
                    "When the customer is ready to order, transition to the ordering flow."
                ),
                tools=["get.options"],
            ),
            Step(
                id="order_entry",
                prompt=(
                    "Help the customer build their order step by step. "
                    "Ask for their coffee preference and size. "
                    "Use `get.options` to check availability. "
                    "Use `add.to.cart` to add items when customer confirms their choice. "
                    "Use `remove_item` if they want to modify their order. "
                    "Use `clear.cart` if they want to start over. "
                    "When they're ready to review and finalize, move to checkout flow."
                ),
                tools=["get.options", "add.to.cart", "clear.cart", "remove.item"],
            ),
            Step(
                id="order_review",
                prompt=(
                    "Review the customer's complete order using `get.summary`. "
                    "Present the total price clearly and confirm all items. "
                    "If customer wants to modify the order, return to order entry. "
                    "When customer confirms, proceed to payment processing."
                ),
                tools=["get.summary"],
            ),
            Step(
                id="payment_processing",
                prompt=(
                    "Process the customer's payment. Ask for their preferred payment method (Card or Cash). "
                    "If paying with cash, ask for the payment amount. "
                    "Use `finalize.order` tool to complete the transaction. "
                    "Provide receipt and thank the customer."
                ),
                tools=["finalize.order"],
            ),
            Step(
                id="order_completed",
                prompt=(
                    "Confirm the order is complete and provide order details. "
                    "Thank the customer and ask if they need anything else. "
                    "If they want to place another order, return to greeting."
                ),
            ),
            Step(
                id="order_cancelled",
                prompt=(
                    "Handle order cancellation gracefully. Use `clear.cart` to remove all items. "
                    "Apologize for any inconvenience and ask if they'd like to try again later."
                ),
                tools=["clear.cart"],
            ),
            Step(
                id="session_end",
                prompt=(
                    "End the session gracefully. Thank the customer for visiting and wish them well. "
                    "Clear any remaining cart items for cleanup."
                ),
                tools=["clear.cart"],
            ),
        )
        .edge(
            Transition(
                from_id="greeting",
                to_id="order_entry",
                when="Customer is ready to place an order or wants to browse menu",
            )
        )
        .edge(
            Transition(
                from_id="order_entry",
                to_id="order_review",
                when="CCustomer wants to review their order or proceed to checkout",
            )
        )
        .edge(
            Transition(
                from_id="order_entry",
                to_id="greeting",
                when="Customer wants to cancel the order completely",
            )
        )
        .edge(
            Transition(
                from_id="order_review",
                to_id="order_entry",
                when="Customer wants to modify their order or add more items",
            )
        )
        .edge(
            Transition(
                from_id="order_review",
                to_id="payment_processing",
                when="Customer confirms the order and wants to proceed with payment",
            )
        )
        .edge(
            Transition(
                from_id="order_review",
                to_id="order_cancelled",
                when="Customer wants to cancel the order",
            )
        )
        .edge(
            Transition(
                from_id="payment_processing",
                to_id="order_completed",
                when="Payment processed successfully",
            )
        )
        .edge(
            Transition(
                from_id="payment_processing",
                to_id="order_review",
                when="Payment fails or customer wants to review order again",
            )
        )
        .edge(
            Transition(
                from_id="order_completed",
                to_id="session_end",
                when="Customer is done and wants to leave",
            )
        )
        .edge(
            Transition(
                from_id="order_completed",
                to_id="greeting",
                when="Customer wants to place another order",
            )
        )
        .edge(
            Transition(
                from_id="order_cancelled",
                to_id="greeting",
                when="Customer wants to try ordering again",
            )
        )
        .edge(
            Transition(
                from_id="order_cancelled",
                to_id="session_end",
                when="Customer wants to leave",
            )
        )
    )

    spec = g.compile()

    # Node overrides for allowed tools
    node_overrides: Dict[str, Dict[str, Any]] = {}
    for node in g._nodes:
        allowed = {
            t
            for t in (node.tools or [])
            if isinstance(t, str) and t in runner._registry
        }
        if allowed:
            node_overrides[node.id] = {"allowed_tools": allowed}

    # Use OpenAI provider
    provider = OpenAI()
    orch = Orchestrator(
        agent=spec,
        provider=provider,
        tool_runner=runner,
        node_overrides=node_overrides,
        verbose=True,
    )
    s = await orch.create_session()

    print("Welcome to Nomos Barista! Type /quit to exit, /pause, /resume, /cancel.")

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

            # Process the response turn - continue until we get a RESPOND
            async for ev in orch.stream(session_id=s.id):
                t = ev.get("type")
                if t == EventType.DECISION_COMPLETED.value:
                    data = ev.get("data", {})
                    if data.get("action") == "RESPOND":
                        response = data.get("response", "")
                        print(f"Agent -> {response}")
                        # Only break on RESPOND - MOVE actions continue processing
                        break
                    elif data.get("action") == "MOVE":
                        # Continue processing for MOVE actions (routing happens automatically)
                        continue
                    else:
                        # Continue for other actions too
                        continue
                # Ignore all other events (no debug prints)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    asyncio.run(main())
