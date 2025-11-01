from nomos.graph import AgentSpec, EdgeSpec, NodeSpec


def test_respond_condition_matches():
    spec = AgentSpec(
        name="demo",
        start="start",
        nodes=[NodeSpec(id="start"), NodeSpec(id="end")],
        edges=[EdgeSpec(from_id="start", to_id="end", when="RESPOND")],
    )
    # RESPOND decision should match and route
    decision = {"action": "RESPOND", "response": "ok"}
    assert spec.route("start", decision) == "end"


def test_end_condition_matches():
    spec = AgentSpec(
        name="demo",
        start="start",
        nodes=[NodeSpec(id="start"), NodeSpec(id="done")],
        edges=[EdgeSpec(from_id="start", to_id="done", when="END")],
    )
    decision = {"action": "END"}
    assert spec.route("start", decision) == "done"

