from nomos.graph import GraphBuilder


def test_graph_builder_instances_do_not_share_state():
    gb1 = GraphBuilder(name="a", start="s1")
    gb1.node("s1").node("n2").edge("s1", "n2")
    gb2 = GraphBuilder(name="b", start="t1")
    gb2.node("t1")
    spec1 = gb1.compile()
    spec2 = gb2.compile()
    assert {n.id for n in spec1.nodes} == {"s1", "n2"}
    assert {n.id for n in spec2.nodes} == {"t1"}
