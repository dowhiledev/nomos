from nomos.graph import Graph, LLMNode, Edge


def test_graph_runtime_compile_to_agent_spec():
    g = Graph(name="demo")
    g.add(
        LLMNode(id="start", prompt="collect"), LLMNode(id="next", prompt="work")
    ).edge(Edge(from_id="start", to_id="next", when="MOVE:next"))
    spec = g.compile()
    assert spec.start == "start"
    # ensure edge/route correspond
    decision = {"action": "MOVE", "step_id": "next"}
    assert spec.route("start", decision) == "next"
