import asyncio
import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType


class Provider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {"type": EventType.TOKEN_EMITTED.value, "data": {"role": "assistant", "delta": "A"}}
        await asyncio.sleep(0.005)
        yield {"type": EventType.DECISION_COMPLETED.value, "data": {"action": "RESPOND", "response": "ok"}}


@pytest.mark.asyncio
async def test_restore_and_continue_flow():
    orch = Orchestrator(agent=None, provider=Provider())
    session = await orch.create_session()

    # Enqueue input to start streaming
    async def consume_first():
        async for ev in orch.stream(session_id=session.id, inputs={"messages": [{"role": "user", "content": [{"type": "text", "data": "go"}]}]}):
            if ev["type"] == EventType.DECISION_COMPLETED.value:
                return

    await consume_first()

    # Create checkpoint then restore
    await orch.control(session_id=session.id, command={"type": "checkpoint.requested", "id": "cp2"})
    await orch.control(session_id=session.id, command={"type": "checkpoint.restore", "id": "cp2"})

    # Send another input and ensure we get a completion again
    completed = False

    async def consume_second():
        nonlocal completed
        async for ev in orch.stream(session_id=session.id, inputs={"messages": [{"role": "user", "content": [{"type": "text", "data": "go2"}]}]}):
            if ev["type"] == EventType.DECISION_COMPLETED.value:
                completed = True
                return

    await consume_second()
    assert completed

