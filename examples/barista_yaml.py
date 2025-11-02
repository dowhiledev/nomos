"""Nomos vNext Barista Example - YAML Configuration Approach

This example demonstrates loading an agent configuration from YAML.
The tools remain in Python while the graph structure is defined declaratively.
"""

import asyncio
from typing import Literal, Optional
import uuid
from pathlib import Path

from dotenv import load_dotenv

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import Graph
from nomos.tools.runner import SimpleToolRunner
from nomos.llms.openai import OpenAI

# Load environment variables
load_dotenv()

# In-memory state (demo only)
_cart: list[dict] = []
_sales: list[dict] = []

# Create tool runner
runner = SimpleToolRunner()


# Tools (same as original barista example)
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
    if balance is not None and balance < 0:
        return (
            f"Insufficient payment amount for the order. Requires ${-balance:.2f} more."
        )
    _sales.append(
        {
            "order_id": str(uuid.uuid4()),
            "total_price": total_price,
            "payment_method": payment_method,
            "payment": payment,
            "balance": balance,
            "items": _cart.copy(),
        }
    )
    clear_cart()
    if balance is not None and balance > 0:
        return (
            f"Order finalized! Total price: ${total_price:.2f}. "
            f"Payment method: {payment_method}. Change: ${balance:.2f}. Thank you for your order!"
        )
    return (
        f"Order finalized! Total price: ${total_price:.2f}. Thank you for your order!"
    )


async def main() -> None:
    # Load the graph from YAML - this is the key difference!
    yaml_path = Path(__file__).parent / "barista_agent.yaml"
    g = Graph.from_yaml(yaml_path)

    # Compile the spec
    spec = g.compile()

    # Use OpenAI provider
    provider = OpenAI()
    orch = Orchestrator(
        agent=spec,
        provider=provider,
        tool_runner=runner,
        verbose=True,
    )
    s = await orch.create_session()

    print(
        "Welcome to Nomos Barista (YAML Configuration)! Type /quit to exit, /pause, /resume, /cancel."
    )

    while True:
        try:
            user_input = input("\n> ").strip()
            if user_input.lower() in ["/quit", "/exit"]:
                print("Thank you for visiting Nomos Barista!")
                break
            elif user_input.lower() == "/pause":
                await orch.pause(s)
                print("Session paused.")
                continue
            elif user_input.lower() == "/resume":
                await orch.resume(s)
                print("Session resumed.")
                continue
            elif user_input.lower() == "/cancel":
                await orch.cancel(s)
                print("Session cancelled.")
                break
            elif user_input.lower() == "/state":
                print(f"Cart: {_cart}")
                print(f"Sales: {_sales}")
                continue
            elif user_input.lower() == "/clear":
                _cart.clear()
                _sales.clear()
                print("State cleared.")
                continue

            if user_input:
                # Send user input
                await orch.input(
                    session_id=s.id,
                    inputs={
                        "messages": [
                            {
                                "role": "user",
                                "content": [{"type": "text", "data": user_input}],
                            }
                        ]
                    },
                )

                # Process the response turn - continue until we get a RESPOND
                async for ev in orch.stream(session_id=s.id):
                    t = ev.type
                    if t == EventType.DECISION_COMPLETED:
                        data = ev.data
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

        except KeyboardInterrupt:
            print("\nGoodbye!")
            break
        except Exception as e:
            print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
