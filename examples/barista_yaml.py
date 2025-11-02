"""Nomos vNext Barista Example - YAML Configuration Approach.

This example demonstrates loading agent configuration declaratively from YAML
while keeping tool implementations in Python. It's ideal for:
- Separating graph/workflow definition from tool code
- Allowing non-programmers to modify workflows (steps and transitions)
- Configuration-driven agent deployment

Compared to barista.py:
- Graph structure is loaded from barista_agent.yaml (declarative)
- Tool implementations remain in Python (imperative)
- Same core functionality but more modular

Architecture:
- barista_agent.yaml: Declarative workflow (steps, transitions, prompts)
- This file: Tool implementations and orchestrator setup
- Graph.from_yaml(): Loads YAML and converts to AgentSpec

Usage:
    $ python examples/barista_yaml.py
    Welcome to Nomos Barista (YAML Configuration)! ...
    > I'd like a medium latte
    Agent: <responds with confirmation>

Special Commands:
    /quit, /exit: Exit the program
    /pause: Pause the orchestrator
    /resume: Resume the orchestrator
    /cancel: Cancel current operation
    /state: Print cart and sales history
    /clear: Reset cart and sales data

Learning Points:
- How to use YAML for graph configuration
- Separation of concerns (declarative config vs imperative tools)
- Dynamic workflow loading from files
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
    """Retrieve available coffee options, sizes, and prices.

    Returns a structured list of available beverages. Used by the agent
    during greeting and order entry phases to inform customers.

    Returns:
        String representation of coffee menu with types, sizes, and prices.
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
    """Calculate the total price of all items in the cart.

    Sums up the price field for all items. Used by add_to_cart and
    get_order_summary to provide real-time totals.

    Returns:
        Total price in dollars (float).
    """
    total_price = sum(item["price"] for item in _cart)
    return total_price


@runner.tool("add.to.cart")
def add_to_cart(coffee_type: str, size: str, price: float) -> str:
    """Add a coffee item to the order cart.

    Assigns a unique UUID to the item and appends to the global _cart.

    Args:
        coffee_type: Coffee type (e.g., "Latte", "Espresso").
        size: Size (e.g., "Small", "Medium", "Large").
        price: Price in dollars.

    Returns:
        Confirmation with item ID and updated total.
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
    """Remove an item from the cart by ID.

    Filters out the item with matching UUID from the global _cart.

    Args:
        item_id: UUID of item to remove.

    Returns:
        Confirmation message.
    """
    global _cart
    _cart = [item for item in _cart if item["item_id"] != item_id]
    return f"Item {item_id} removed successfully."


@runner.tool("get.summary")
async def get_order_summary() -> str:
    """Retrieve formatted summary of all cart items.

    Displays all items with details and total. Returns empty message if
    cart is empty. Includes small async delay for demo realism.

    Returns:
        Formatted order summary or empty message.
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
    """Clear all items from the order cart.

    Empties the global _cart list. Used during order cancellation and
    session cleanup.

    Returns:
        Confirmation message.
    """
    global _cart
    _cart = []
    return "All items cleared successfully."


@runner.tool("finalize.order", timeout=5)
async def finalize_order(
    payment_method: Literal["Card", "Cash"], payment: Optional[float] = None
) -> str:
    """Finalize the order and process payment.

    Records the sale to _sales history, validates payment if Cash,
    and clears the cart. Returns receipt with order ID and change.

    Args:
        payment_method: "Card" or "Cash".
        payment: Payment amount (required for Cash, optional for Card).

    Returns:
        Confirmation message with order details or error message.

    Raises:
        TimeoutError: If operation exceeds 5 second timeout.
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
    """Run the interactive barista agent with YAML configuration.

    Key Differences from barista.py:
    1. Graph is loaded from barista_agent.yaml (declarative)
    2. Same tool implementations as barista.py
    3. Additional debug commands (/state, /clear)

    Workflow:
    1. Load graph spec from YAML file
    2. Compile to AgentSpec
    3. Create orchestrator with OpenAI provider
    4. Enter REPL loop for user interaction
    5. Stream responses until RESPOND action

    Control Commands:
    - /quit, /exit: Exit
    - /pause, /resume, /cancel: Session control
    - /state: Print cart and sales
    - /clear: Reset state

    This approach is ideal for production deployments where workflows
    are managed separately from implementation code.
    """
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
