"""Test barista graph construction."""

import pytest

from examples.barista import Graph, Step, Transition


def test_barista_graph_compilation():
    """Test that the barista graph compiles correctly."""
    # Create a simplified version of the barista graph
    g = Graph(name="barista").add(
        Step(
            id="greeting",
            prompt="Greet the customer warmly.",
            tools=["get.options"],
        ),
        Step(
            id="order_entry",
            prompt="Help the customer build their order.",
            tools=["get.options", "add.to.cart"],
        ),
        Transition(
            from_id="greeting",
            to_id="order_entry",
            when="Customer is ready to place an order",
        ),
    )
    
    # Test compilation
    spec = g.compile()
    
    # Verify the spec
    assert spec.name == "barista"
    assert spec.start == "greeting"
    assert len(spec.nodes) == 2
    assert len(spec.edges) == 1
    
    # Check tools are preserved
    greeting_tools = spec.get_node_tools("greeting")
    assert greeting_tools == ["get.options"]
    
    order_tools = spec.get_node_tools("order_entry")
    assert "get.options" in order_tools
    assert "add.to.cart" in order_tools
