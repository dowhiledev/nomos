from nomos.graph import Graph, Step, Transition


def test_graph_runtime_compile_to_agent_spec():
    g = Graph(name="demo")
    g.add(Step(id="start", prompt="collect"), Step(id="next", prompt="work")).edge(
        Transition(from_id="start", to_id="next", when="MOVE:next")
    )
    spec = g.compile()
    assert spec.start == "start"
    # ensure edge/route correspond
    decision = {"action": "MOVE", "step_id": "next"}
    assert spec.route("start", decision) == "next"
