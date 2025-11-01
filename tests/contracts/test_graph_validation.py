import pytest

from nomos.graph import AgentSpec, NodeSpec, EdgeSpec
from nomos.graph.spec import compile_agent


def test_valid_agent_compiles():
    spec = AgentSpec(
        name="demo",
        start="a",
        nodes=[NodeSpec(id="a"), NodeSpec(id="b")],
        edges=[EdgeSpec(from_id="a", to_id="b", when="MOVE:b")],
    )
    out = compile_agent(spec)
    assert out.start == "a"


def test_invalid_start_raises():
    spec = AgentSpec(name="demo", start="x", nodes=[NodeSpec(id="a")], edges=[])
    with pytest.raises(ValueError):
        compile_agent(spec)


def test_invalid_edge_nodes_raise():
    spec = AgentSpec(
        name="demo",
        start="a",
        nodes=[NodeSpec(id="a")],
        edges=[EdgeSpec(from_id="a", to_id="b", when="MOVE:b")],
    )
    with pytest.raises(ValueError):
        compile_agent(spec)

