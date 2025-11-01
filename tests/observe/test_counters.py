import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.core.observe import EVENT_COUNTERS, reset_counters


class Provider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {"type": EventType.TOKEN_EMITTED.value, "data": {"role": "assistant", "delta": "x"}}
        yield {"type": EventType.DECISION_COMPLETED.value, "data": {"action": "RESPOND", "response": "ok"}}


@pytest.mark.asyncio
async def test_event_counters_increment():
    reset_counters()
    orch = Orchestrator(agent=None, provider=Provider())
    session = await orch.create_session()
    async for _ in orch.stream(session_id=session.id, inputs={"messages": [{"role": "user", "content": [{"type": "text", "data": "hi"}]}]}):
        if EVENT_COUNTERS.get(EventType.DECISION_COMPLETED.value):
            break
    assert EVENT_COUNTERS.get(EventType.SESSION_CREATED.value) == 1
    assert EVENT_COUNTERS.get(EventType.INPUT_ENQUEUED.value) == 1
    assert EVENT_COUNTERS.get(EventType.TOKEN_EMITTED.value) >= 1
    assert EVENT_COUNTERS.get(EventType.DECISION_COMPLETED.value) == 1

