import asyncio
from typing import Any, AsyncIterator, Dict, List

import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType


class FakeProviderToolCall:
    async def stream_decision(self, messages: List[Dict[str, Any]], schema: Any) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Emit a decision asking to call a tool
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {
                "action": "TOOL_CALL",
                "tool_call": {"tool_name": "web.search", "tool_kwargs": {"query": "tokyo"}},
            },
        }


class FakeToolRunner:
    async def run(self, tool_name: str, args: Dict[str, Any], ctx: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        yield {"type": "tool.started", "tool": tool_name}
        await asyncio.sleep(0.005)
        yield {"type": "tool.completed", "result": {"items": [1, 2, 3]}}


@pytest.mark.asyncio
async def test_orchestrator_handles_tool_call():
    orch = Orchestrator(agent=None, provider=FakeProviderToolCall(), tool_runner=FakeToolRunner())
    session = await orch.create_session()

    inputs = {"messages": [{"role": "user", "content": [{"type": "text", "data": "hi"}]}]}

    seen_started = False
    seen_completed = False

    async def consume():
        async for ev in orch.stream(session_id=session.id, inputs=inputs):
            if ev["type"] == "tool.started":
                nonlocal seen_started
                seen_started = True
            if ev["type"] == "tool.completed":
                nonlocal seen_completed
                seen_completed = True
                return

    await consume()
    assert seen_started and seen_completed

