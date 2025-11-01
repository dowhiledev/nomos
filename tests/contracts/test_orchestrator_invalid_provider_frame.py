import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType


class BadProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        # Missing data in token frame
        yield {"type": EventType.TOKEN_EMITTED.value}


@pytest.mark.asyncio
async def test_orchestrator_handles_invalid_provider_frame():
    orch = Orchestrator(agent=None, provider=BadProvider())
    s = await orch.create_session()
    saw_error = False

    async def consume():
        nonlocal saw_error
        async for ev in orch.stream(
            session_id=s.id,
            inputs={
                "messages": [
                    {"role": "user", "content": [{"type": "text", "data": "hi"}]}
                ]
            },
        ):
            if ev["type"] == EventType.ERROR_OCCURRED.value:
                saw_error = True
                return

    await consume()
    assert saw_error
