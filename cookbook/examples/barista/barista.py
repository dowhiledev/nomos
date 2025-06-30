import os

# Enable Debugging
os.environ["NOMOS_LOG_LEVEL"] = "DEBUG"
os.environ["NOMOS_ENABLE_LOGGING"] = "true"

from nomos import *
from nomos.llms import OpenAI
from nomos.models.flow import FlowConfig
from nomos.memory.flow import FlowMemoryComponent
from barista_tools import tools

# Step Definitions for Order Taking Flow
greeting_step = Step(
    step_id="greeting",
    description=(
        "Greet the customer warmly and ask how you can help them today. "
        "Use the `get_available_coffee_options` tool to get familiar with available options. "
        "If the customer mentions a specific coffee preference, check if it's available. "
        "When the customer is ready to order, transition to the ordering flow."
    ),
    available_tools=["get_available_coffee_options"],
    routes=[
        Route(
            target="order_entry",
            condition="Customer is ready to place an order or wants to browse menu",
        )
    ],
)

order_entry_step = Step(
    step_id="order_entry",
    description=(
        "Help the customer build their order step by step. "
        "Ask for their coffee preference and size. "
        "Use `get_available_coffee_options` to check availability. "
        "Use `add_to_cart` to add items when customer confirms their choice. "
        "Use `remove_item` if they want to modify their order. "
        "Use `clear_cart` if they want to start over. "
        "When they're ready to review and finalize, move to checkout flow."
    ),
    available_tools=[
        "get_available_coffee_options",
        "add_to_cart",
        "remove_item",
        "clear_cart",
    ],
    routes=[
        Route(
            target="order_review",
            condition="Customer wants to review their order or proceed to checkout",
        ),
        Route(
            target="greeting",
            condition="Customer wants to cancel the order completely",
        ),
    ],
)

# Step Definitions for Checkout Flow
order_review_step = Step(
    step_id="order_review",
    description=(
        "Review the customer's complete order using `get_order_summary`. "
        "Present the total price clearly and confirm all items. "
        "If customer wants to modify the order, return to order entry. "
        "When customer confirms, proceed to payment processing."
    ),
    available_tools=["get_order_summary"],
    routes=[
        Route(
            target="order_entry",
            condition="Customer wants to modify their order or add more items",
        ),
        Route(
            target="payment_processing",
            condition="Customer confirms the order and wants to proceed with payment",
        ),
        Route(
            target="order_cancelled",
            condition="Customer wants to cancel the order",
        ),
    ],
)

payment_processing_step = Step(
    step_id="payment_processing",
    description=(
        "Process the customer's payment. Ask for their preferred payment method (Card or Cash). "
        "If paying with cash, ask for the payment amount. "
        "Use `finalize_order` tool to complete the transaction. "
        "Provide receipt and thank the customer."
    ),
    available_tools=["finalize_order"],
    routes=[
        Route(
            target="order_completed",
            condition="Payment is processed successfully",
        ),
        Route(
            target="order_review",
            condition="Payment fails or customer wants to review order again",
        ),
    ],
)

order_completed_step = Step(
    step_id="order_completed",
    description=(
        "Confirm the order is complete and provide order details. "
        "Thank the customer and ask if they need anything else. "
        "If they want to place another order, return to greeting."
    ),
    available_tools=[],
    routes=[
        Route(
            target="greeting",
            condition="Customer wants to place another order",
        ),
        Route(
            target="session_end",
            condition="Customer is done and wants to leave",
        ),
    ],
)

order_cancelled_step = Step(
    step_id="order_cancelled",
    description=(
        "Handle order cancellation gracefully. Use `clear_cart` to remove all items. "
        "Apologize for any inconvenience and ask if they'd like to try again later."
    ),
    available_tools=["clear_cart"],
    routes=[
        Route(
            target="greeting",
            condition="Customer wants to try ordering again",
        ),
        Route(
            target="session_end",
            condition="Customer wants to leave",
        ),
    ],
)

session_end_step = Step(
    step_id="session_end",
    description=(
        "End the session gracefully. Thank the customer for visiting and wish them well. "
        "Clear any remaining cart items for cleanup."
    ),
    available_tools=["clear_cart"],
    routes=[],
)

# Define Flow Configurations
ordering_flow_config = FlowConfig(
    flow_id="ordering_flow",
    enters=["greeting", "order_entry"],  # Entry points into this flow
    exits=["order_review"],  # Exit points to other flows
    description="Handle customer greeting and order taking process",
    components={
        "memory": {
            "llm": {
                "provider": "openai",
                "model": "gpt-4o-mini",
            },
            "retriever": {
                "method": "embedding",
            },
        }
    },
)

checkout_flow_config = FlowConfig(
    flow_id="checkout_flow",
    enters=["order_review"],  # Enters from ordering flow
    exits=["order_completed", "order_cancelled", "session_end"],  # Multiple exit points
    description="Handle order review, payment processing and completion",
    memory_config={
        "retriever_k": 3,
        "summary_length": 100,
    },
    components={
        "memory": {
            "type": "flow_memory",
            "config": {
                "retriever_k": 3,
                "summary_length": 100,
            },
        }
    },
)

# Create agent configuration with flows
agent_config = AgentConfig(
    name="barista",
    persona=(
        "You are a helpful barista assistant at 'Starbucks'. You are kind and polite. "
        "When responding, you use human-like natural language, professionally and politely. "
        "You have a good memory for customer preferences within their current visit."
    ),
    steps=[
        greeting_step,
        order_entry_step,
        order_review_step,
        payment_processing_step,
        order_completed_step,
        order_cancelled_step,
        session_end_step,
    ],
    start_step_id="greeting",
    flows=[ordering_flow_config, checkout_flow_config],
)

# Initialize the LLM and Nomos agent
llm = OpenAI()
barista = Agent.from_config(config=agent_config, llm=llm, tools=tools)

# Create a new session
sess = barista.create_session()

# Simulating a conversation (You can use fastapi or any other method to get user input)
user_input = None
while True:
    decision, _ = sess.next(user_input)
    if decision.action in [Action.ASK, Action.ANSWER]:
        user_input = input(f"Assistant: {decision.response}\nYou: ")
    elif decision.action == Action.END:
        print("Session ended.")
        break
    else:
        print("Unknown action. Exiting.")
        break

_save = input("Do you want to save the session? (y/n): ")
if _save.lower() == "y":
    # Save the session
    sess.save_session()
