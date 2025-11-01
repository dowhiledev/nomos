from nomos.graph import AgentSpec, NodeSpec, EdgeSpec
from nomos.graph.prompt import edge_conditions_for_prompt


def test_edge_conditions_for_prompt_lists_targets():
    spec = AgentSpec(
        name="demo",
        start="start",
        nodes=[NodeSpec(id="start"), NodeSpec(id="end"), NodeSpec(id="loop")],
        edges=[
            EdgeSpec(from_id="start", to_id="end", condition="user wants to finish"),
            EdgeSpec(from_id="start", to_id="loop", condition="needs more info"),
        ],
    )
    txt = edge_conditions_for_prompt(spec, "start")
    assert "to 'end': user wants to finish" in txt
    assert "to 'loop': needs more info" in txt

