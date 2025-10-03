from nomos import step, tool, Agent, Step, Route
import uuid

class BaristaAgent(Agent):
    __persona__ = (
        "You are a helpful barista assistant at 'Starbucks'. You are kind and polite. "
        "When responding, you use human-like natural language, professionally and politely. "
        "You have a good memory for customer preferences within their current visit."
    )

    def __session_init__(self):
        self.coffee_cart = []

    @tool
    def get_available_coffee_options(self) -> str:
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

    @tool
    def add_to_cart(self, coffee_type: str, size: str, price: float) -> str:
        """
        Add a coffee item to the cart.
        """
        item_id = str(uuid.uuid4())
        self.coffee_cart.append(
            {
                "item_id": item_id,
                "coffee_type": coffee_type,
                "size": size,
                "price": price,
            }
        )
        current_total = self.get_total_price()
        return f"Item {item_id} added to cart. Current total: ${current_total:.2f}"
    
    @tool
    def get_total_price(self) -> float:
        """
        Calculate the total price of all orders in the cart.
        """
        total_price = sum(item["price"] for item in self.coffee_cart)
        return total_price
    
    @tool
    def remove_item(self, item_id: str) -> str:
        """
        Remove an item from the cart by item_id.
        """
        initial_count = len(self.coffee_cart)
        self.coffee_cart = [item for item in self.coffee_cart if item["item_id"] != item_id]
        if len(self.coffee_cart) < initial_count:
            current_total = self.get_total_price()
            return f"Item {item_id} removed from cart. Current total: ${current_total:.2f}"
        else:
            return f"Item {item_id} not found in cart."
        
    @tool
    def clear_cart(self) -> str:
        """
        Clear all items from the cart.
        """
        self.coffee_cart = []
        return "Cart cleared successfully."
    
    @tool
    def get_order_summary(self) -> str:
        """
        Get a summary of the current order.
        """
        if not self.coffee_cart:
            return "Your cart is empty."
        
        summary_lines = []
        for item in self.coffee_cart:
            summary_lines.append(f"Item ID: {item['item_id']}, Type: {item['coffee_type']}, Size: {item['size']}, Price: ${item['price']:.2f}")
        
        total_price = self.get_total_price()
        summary_lines.append(f"Total Price: ${total_price:.2f}")
        
        return "\n".join(summary_lines)
    
    @tool
    def finalize_order(self, payment_method: str, amount_paid: float) -> str:
        """
        Finalize the order with payment.
        """
        total_price = self.get_total_price()
        if amount_paid < total_price:
            return f"Insufficient payment. Total price is ${total_price:.2f}, but received ${amount_paid:.2f}."
        
        change = amount_paid - total_price
        self.coffee_cart = []  # Clear cart after finalizing order
        return f"Payment of ${amount_paid:.2f} received via {payment_method}. Change: ${change:.2f}. Thank you for your purchase!"
    
    @step(start=True)
    def greeting_step(self):
        return Step(
            step_id="greeting",
            description=(
                "Greet the customer warmly. Ask if they would like to see the menu or have a specific order in mind."
            ),
            available_tools=[self.get_available_coffee_options],
            routes=[
                Route(
                    target=self.order_entry_step,
                    condition="Customer is ready to place an order",
                )
            ]
        )
    @step
    def order_entry_step(self):
        return Step(
            step_id="order_entry",
            description=(
                "Take the customer's order. Ask for the coffee type, size, and any customizations."
            ),
            available_tools=[self.get_available_coffee_options, self.add_to_cart, self.remove_item, self.clear_cart],
            routes=[
                Route(
                    target=self.order_review_step,
                    condition="Customer wants to review their order",
                ),
                Route(
                    target=self.greeting_step,
                    condition="Customer wants to cancel the order",
                )
            ]
        )
    
    @step
    def order_review_step(self):
        return Step(
            step_id="order_review",
            description=(
                "Review the customer's order. Present the order summary and total price."
            ),
            available_tools=[self.get_order_summary],
            routes=[
                Route(
                    target=self.order_entry_step,
                    condition="Customer wants to modify their order",
                ),
                Route(
                    target=self.payment_step,
                    condition="Customer confirms the order",
                ),
                Route(
                    target=self.order_cancellation_step,
                    condition="Customer wants to cancel the order",
                )
            ]
        )

    @step
    def payment_step(self):
        return Step(
            step_id="payment",
            description=(
                "Handle the payment process. Collect payment information and confirm the order."
            ),
            available_tools=[self.finalize_order],
            routes=[
                Route(
                    target=self.greeting_step,
                    condition="Customer wants to start a new order",
                ),
                Route(
                    target=self.order_cancellation_step,
                    condition="Customer wants to cancel the order",
                ),
                Route(
                    target=self.checkout_step,
                    condition="Payment successful and order finalized",
                )
            ]
        )

    @step
    def checkout_step(self):
        return Step(
            step_id="checkout",
            description=(
                "Handle the checkout process. Confirm the order has been finalized and thank the customer."
            ),
            available_tools=[],
            routes=[
                Route(
                    target=self.greeting_step,
                    condition="Customer wants to start a new order",
                )
            ]
        )

    @step
    def order_cancellation_step(self):
        return Step(
            step_id="order_cancellation",
            description=(
                "Handle the order cancellation process."
            ),
            available_tools=[self.clear_cart],
            routes=[
                Route(
                    target=self.greeting_step,
                    condition="Customer wants to start a new order",
                )
            ]
        )
    
    @property
    def steps(self) -> list[Step]:
        """Return the list of steps in the workflow. This is in the Base class."""
        pass
    
    @property
    def tools(self) -> list:
        """Return the list of tools available to the agent. This is in the Base class."""
        pass

    @property
    def start_step(self) -> Step:
        """Return the ID of the starting step. This is in the Base class."""
        pass

    @property
    def flows(self) -> dict:
        """Return the flows of the agent. This is in the Base class."""
        pass

    @property
    def app(self):
        """Return the FastAPI app instance. This is in the Base class."""
        pass

    def run(self):
        """Run the agent in the console. Uses Typer under the hood. This is in the Base class."""
        pass

barista = BaristaAgent()

if __name__ == "__main__":
    # import uvicorn
    # uvicorn.run(barista.app, host="0.0.0.0", port=8000)

    barista.run()