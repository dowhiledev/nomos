import pytest

from nomos.core import Orchestrator
from nomos.graph import AgentSpec, EdgeSpec, NodeSpec


class FakeProviderMove:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        # Immediately emit a MOVE decision to 'next'
        yield {
            "type": "decision.completed",
            "data": {"action": "MOVE", "step_id": "next"},
        }


@pytest.mark.asyncio
async def test_orchestrator_applies_routing_and_updates_state():
    agent = AgentSpec(
        name="demo",
        start="start",
        nodes=[NodeSpec(id="start"), NodeSpec(id="next")],
        edges=[EdgeSpec(from_id="start", to_id="next", when="MOVE:next")],
    )
    orch = Orchestrator(agent=agent, provider=FakeProviderMove())
    session = await orch.create_session()

    inputs = {
        "messages": [{"role": "user", "content": [{"type": "text", "data": "go"}]}]
    }

    routed = False

    async def consume():
        nonlocal routed
        async for ev in orch.stream(session_id=session.id, inputs=inputs):
            if ev.type == "routing.applied":
                routed = True
                return

    await consume()
    assert routed
    st = await orch.materialize_state(session_id=session.id)
    assert st.current_node == "next"
