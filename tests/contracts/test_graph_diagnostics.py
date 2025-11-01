import pytest

from nomos.graph.spec import AgentSpec, EdgeSpec, NodeSpec, compile_agent


def test_duplicate_edges_raise():
    spec = AgentSpec(
        name="demo",
        start="a",
        nodes=[NodeSpec(id="a"), NodeSpec(id="b")],
        edges=[
            EdgeSpec(from_id="a", to_id="b", condition="go to b"),
            EdgeSpec(from_id="a", to_id="b", condition="go to b"),
        ],
    )
    with pytest.raises(ValueError):
        compile_agent(spec)


def test_unreachable_nodes_raise():
    spec = AgentSpec(
        name="demo",
        start="a",
        nodes=[NodeSpec(id="a"), NodeSpec(id="b"), NodeSpec(id="c")],
        edges=[EdgeSpec(from_id="a", to_id="b", condition="go to b")],
    )
    with pytest.raises(ValueError):
        compile_agent(spec)
