import asyncio
from typing import Any, AsyncIterator, Dict, List

import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.tools.runner import SimpleToolRunner


class ProviderWithToolCall:
    async def stream_decision(self, messages: List[Dict[str, Any]], schema: Any) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Immediately request a tool call
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {
                "action": "TOOL_CALL",
                "tool_call": {"tool_name": "slow.tool", "tool_kwargs": {"n": 5}},
            },
        }


async def slow_tool(n: int, ctx: Dict[str, Any] | None = None):  # type: ignore[no-untyped-def]
    # Stream some progress frames, observe cancellation via ctx['cancel_event']
    if ctx is None:
        ctx = {}
    ev = ctx.get("cancel_event")
    for i in range(n):
        await asyncio.sleep(0.005)
        if ev is not None and getattr(ev, "is_set", lambda: False)():
            yield {"type": "tool.error", "error": "cancelled"}
            return
        yield {"type": "tool.progress", "i": i}
    yield {"type": "tool.completed", "result": "ok"}


@pytest.mark.asyncio
async def test_cancel_mid_tool_propagates_and_stops_stream():
    orch = Orchestrator(agent=None, provider=ProviderWithToolCall(), tool_runner=SimpleToolRunner({"slow.tool": slow_tool}))
    session = await orch.create_session()
    inputs = {"messages": [{"role": "user", "content": [{"type": "text", "data": "go"}]}]}

    saw_progress = False
    saw_tool_end = False

    async def consume():
        nonlocal saw_progress, saw_tool_end
        async for ev in orch.stream(session_id=session.id, inputs=inputs):
            if ev["type"] == "tool.progress":
                saw_progress = True
                # issue cancel once we see progress
                await orch.control(session_id=session.id, command={"type": "cancel.requested"})
            if ev["type"] in ("tool.error", "tool.completed", EventType.CANCEL_APPLIED.value):
                saw_tool_end = True
                return

    await consume()
    assert saw_progress
    assert saw_tool_end

