import asyncio
from typing import Any, AsyncIterator, Dict, List

import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.graph import AgentSpec, NodeSpec, EdgeSpec
from nomos.tools.agent_adapter import as_tool
from nomos.tools.runner import SimpleToolRunner


class ParentProvider:
    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Ask to call the sub-agent tool
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {
                "action": "TOOL_CALL",
                "tool_call": {
                    "tool_name": "sub.agent",
                    "tool_kwargs": {"messages": messages},
                },
            },
        }


class ChildProvider:
    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "nested..."},
        }
        await asyncio.sleep(0.001)
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": "nested ok"},
        }


@pytest.mark.asyncio
async def test_agent_as_tool_adapter_end_to_end():
    # simple 2-node agent for child (not strictly required for this test)
    child_agent = AgentSpec(
        name="child",
        start="a",
        nodes=[NodeSpec(id="a"), NodeSpec(id="b")],
        edges=[EdgeSpec(from_id="a", to_id="b", condition="MOVE:b")],
    )
    tool = as_tool(child_agent, provider=ChildProvider())
    runner = SimpleToolRunner({"sub.agent": tool})
    orch = Orchestrator(agent=None, provider=ParentProvider(), tool_runner=runner)
    session = await orch.create_session()

    tokens = []
    completed = False

    async def consume():
        nonlocal tokens, completed
        async for ev in orch.stream(
            session_id=session.id,
            inputs={
                "messages": [
                    {"role": "user", "content": [{"type": "text", "data": "hi"}]}
                ]
            },
        ):
            if ev["type"] == "tool.stdout":
                tokens.append(ev["line"])  # type: ignore[index]
            if ev["type"] == "tool.completed":
                completed = True
                return

    await consume()
    assert tokens
    assert completed
