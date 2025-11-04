"""Nomos vNext Barista Example - Interactive Coffee Ordering Agent.

This example demonstrates a conversational agent that helps customers order coffee.
The agent uses a graph-based workflow with multiple states (greeting → order entry →
review → payment → completion) and tools for managing the order lifecycle.

Architecture:
- Graph-based state machine with 7 nodes for different conversation phases
- OpenAI LLM provider for natural language understanding and generation
- SimpleToolRunner managing 6 tools (get options, add/remove items, finalize order, etc)
- In-memory cart and sales history (for demo purposes)

How It Works:
1. Agent greets customer and explains available options
2. Customer builds order step-by-step using tools
3. Agent reviews order and confirms total price
4. Agent processes payment (Cash or Card)
5. Agent confirms completion or offers to place another order

Usage:
    $ python examples/barista.py
    Welcome to Nomos Barista! Type /quit to exit, /pause, /resume, /cancel.
    You: I'd like a medium latte
    Agent: <responds with confirmation>

Environment:
    Requires OPENAI_API_KEY environment variable set (loaded via dotenv).

Learning Points:
- How to define multi-step workflows with routing conditions
- Using tools for stateful operations (cart management)
- Streaming agent responses in an async loop
- Interactive session control (pause, resume, cancel)
"""

import asyncio
from typing import Literal, Optional
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
def get_available_coffee_options() -> list[dict]:
    """Retrieve available coffee options, sizes, and prices.

    Returns a structured list of available beverages with their size options
    and corresponding prices. Used during greeting and order entry phases.

    Returns:
        List of coffee options with types, sizes, and prices.

    Example:
        >>> result = await get_available_coffee_options()
        >>> # result contains list of coffee options
    """
    return [
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


def get_total_price() -> float:
    """Calculate the total price of all items in the cart.

    Sums the 'price' field for all items in the global _cart list.
    Used by add_to_cart and get_order_summary to provide real-time totals.

    Returns:
        Total price in dollars (float).

    Example:
        >>> _cart = [{"price": 3.5}, {"price": 2.0}]
        >>> get_total_price()
        5.5
    """
    total_price = sum(item["price"] for item in _cart)
    return total_price


@runner.tool("add.to.cart")
async def add_to_cart(coffee_type: str, size: str) -> str:
    """Add a coffee item to the order cart.

    Appends a new item to the global _cart list with a unique UUID.
    Used during order entry phase when customer confirms their selection.

    Args:
        coffee_type: Type of coffee (e.g., "Latte", "Espresso", "Cappuccino").
        size: Size of the drink (e.g., "Small", "Medium", "Large").

    Returns:
        Confirmation message with item ID and updated cart total.

    Example:
        >>> add_to_cart("Latte", "Medium", 3.5)
        "Item abc-123 added to cart. Current total: $3.50"
    """
    global _cart
    item_id = str(uuid.uuid4())
    coffee_options = get_available_coffee_options()
    assert coffee_type in [opt["type"] for opt in coffee_options], "Invalid coffee type"
    assert size in ["Small", "Medium", "Large"], "Invalid size"
    price = next(
        opt["prices"][opt["sizes"].index(size)]
        for opt in coffee_options
        if opt["type"] == coffee_type
    )
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
    """Remove an item from the order cart by ID.

    Filters the global _cart list to remove the item with the matching UUID.
    Used when customers want to modify their order during order entry.

    Args:
        item_id: UUID of the item to remove (from add_to_cart response).

    Returns:
        Confirmation message that the item was removed.

    Example:
        >>> remove_item("abc-123")
        "Item abc-123 removed successfully."
    """
    global _cart
    assert any(item["item_id"] == item_id for item in _cart), "Item ID not found in cart"
    _cart = [item for item in _cart if item["item_id"] != item_id]
    return f"Item {item_id} removed successfully."


@runner.tool("get.summary")
async def get_order_summary() -> str:
    """Retrieve a formatted summary of all items in the cart.

    Iterates through the global _cart list and formats each item with
    details (ID, type, size, price). Returns empty message if cart is empty.
    Includes a small async delay to simulate real-world operations.

    Returns:
        Formatted string with item details and total price, or empty message.

    Example:
        >>> await get_order_summary()
        "Order Summary:
        Item ID: abc-123, Coffee: Latte, Size: Medium, Price: $3.50
        Total Price: $3.50"
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

    Empties the global _cart list completely. Used when customers cancel
    their order or start over, and also during order completion cleanup.

    Returns:
        Confirmation message that the cart was cleared.

    Example:
        >>> clear_cart()
        "All items cleared successfully."
    """
    global _cart
    _cart = []
    return "All items cleared successfully."


@runner.tool("finalize.order", timeout=5)
async def finalize_order(
    payment_method: Literal["Card", "Cash"], payment: Optional[float] = None
) -> str:
    """Finalize the order and process payment.

    Validates payment information, records the sale to _sales history,
    clears the cart, and returns a completion message with receipt details.

    For Cash payments, validates that payment amount is sufficient.
    For Card payments, skips amount validation (amount can be None).

    Args:
        payment_method: "Card" or "Cash".
        payment: Payment amount in dollars (required for Cash, optional for Card).

    Returns:
        Confirmation message with order ID, total, and change (if applicable).
        Error message if cart is empty or payment is insufficient.

    Raises:
        TimeoutError: If operation exceeds 5 second timeout.

    Example:
        >>> await finalize_order("Cash", 20.0)
        "Order finalized! Total price: $15.50. Change: $4.50. Thank you!"
        >>> await finalize_order("Card", None)
        "Order finalized! Total price: $15.50. Thank you for your order!"
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
            "balance": payment - total_price if payment else None,
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
    """Run the interactive barista agent.

    Initializes the graph-based coffee ordering workflow, creates an orchestrator,
    and enters a REPL loop that:
    1. Accepts user input from stdin
    2. Sends input to the orchestrator
    3. Streams agent responses until a RESPOND action
    4. Prints the agent's response

    Supports control commands:
    - /quit: Exit the program
    - /pause: Pause the orchestrator
    - /resume: Resume the orchestrator
    - /cancel: Cancel the current operation

    The workflow includes 7 nodes:
    - greeting: Welcome and menu exploration
    - order_entry: Build order with add/remove
    - order_review: Confirm order and price
    - payment_processing: Handle payment
    - order_completed: Confirmation and offer for another order
    - order_cancelled: Cancellation handling
    - session_end: Graceful exit
    """
    # Define the graph
    g = Graph(name="barista").add(
        # Steps
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
        # Transitions
        Transition(
            from_id="greeting",
            to_id="order_entry",
            when="Customer is ready to place an order or wants to browse menu",
        ),
        Transition(
            from_id="order_entry",
            to_id="order_review",
            when="Customer wants to review their order or proceed to checkout",
        ),
        Transition(
            from_id="order_entry",
            to_id="greeting",
            when="Customer wants to cancel the order completely",
        ),
        Transition(
            from_id="order_review",
            to_id="order_entry",
            when="Customer wants to modify their order or add more items",
        ),
        Transition(
            from_id="order_review",
            to_id="payment_processing",
            when="Customer confirms the order and wants to proceed with payment",
        ),
        Transition(
            from_id="order_review",
            to_id="order_cancelled",
            when="Customer wants to cancel the order",
        ),
        Transition(
            from_id="payment_processing",
            to_id="order_completed",
            when="Payment processed successfully",
        ),
        Transition(
            from_id="payment_processing",
            to_id="order_review",
            when="Payment fails or customer wants to review order again",
        ),
        Transition(
            from_id="order_completed",
            to_id="session_end",
            when="Customer is done and wants to leave",
        ),
        Transition(
            from_id="order_completed",
            to_id="greeting",
            when="Customer wants to place another order",
        ),
        Transition(
            from_id="order_cancelled",
            to_id="greeting",
            when="Customer wants to try ordering again",
        ),
        Transition(
            from_id="order_cancelled",
            to_id="session_end",
            when="Customer wants to leave",
        ),
    )

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
                # Ignore all other events (no debug prints)
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    asyncio.run(main())
