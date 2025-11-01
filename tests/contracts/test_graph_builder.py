from nomos.graph import GraphBuilder


def test_graph_builder_compile_and_route():
    gb = GraphBuilder(name="demo", start="start")
    gb.node("start", prompt="collect").node("next", prompt="work").edge(
        "start", "next", condition="user proceeds to next"
    )
    spec = gb.compile()
    assert spec.start == "start"
    # a MOVE decision to 'next' should route
    decision = {"action": "MOVE", "step_id": "next"}
    assert spec.route("start", decision) == "next"
