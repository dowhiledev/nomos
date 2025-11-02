import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import AgentSpec, NodeSpec, EdgeSpec
from nomos.tools.runner import SimpleToolRunner


class ProviderA:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": "A"},
        }


class ProviderB:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": "B"},
        }


@pytest.mark.asyncio
async def test_node_level_provider_override_applied():
    spec = AgentSpec(
        name="demo",
        start="start",
        nodes=[NodeSpec(id="start"), NodeSpec(id="next")],
        edges=[EdgeSpec(from_id="start", to_id="next", condition="MOVE:next")],
    )
    orch = Orchestrator(
        agent=spec,
        provider=ProviderA(),
        node_overrides={"start": {"provider": ProviderB()}},
    )
    s = await orch.create_session()
    events = []
    async for ev in orch.stream(
        session_id=s.id,
        inputs={
            "messages": [{"role": "user", "content": [{"type": "text", "data": "hi"}]}]
        },
    ):
        events.append(ev)
        if ev.type == EventType.DECISION_COMPLETED:
            break
    assert events[-1].data["response"] == "B"


class ProviderTool:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {
                "action": "TOOL_CALL",
                "tool_call": {"tool_name": "only", "tool_kwargs": {}},
            },
        }


async def only_tool():
    yield {"type": "tool.completed", "result": True}


@pytest.mark.asyncio
async def test_node_level_allowed_tools_filter():
    spec = AgentSpec(name="demo", start="start", nodes=[NodeSpec(id="start")], edges=[])
    runner = SimpleToolRunner({"only": only_tool, "blocked": only_tool})
    orch = Orchestrator(
        agent=spec,
        provider=ProviderTool(),
        tool_runner=runner,
        node_overrides={"start": {"allowed_tools": {"only"}}},
    )
    s = await orch.create_session()
    completed = False

    async def consume():
        nonlocal completed
        async for ev in orch.stream(
            session_id=s.id,
            inputs={
                "messages": [
                    {"role": "user", "content": [{"type": "text", "data": "go"}]}
                ]
            },
        ):
            if ev.type == EventType.TOOL_COMPLETED:
                completed = True
                return

    await consume()
    assert completed
