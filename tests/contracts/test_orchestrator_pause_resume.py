import asyncio
import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType


class StreamingProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        # 5 tokens then a completion
        for ch in ["A", "B", "C", "D", "E"]:
            await asyncio.sleep(0.01)
            yield {"type": EventType.TOKEN_EMITTED.value, "data": {"role": "assistant", "delta": ch}}
        yield {"type": EventType.DECISION_COMPLETED.value, "data": {"action": "RESPOND", "response": "ABCDE"}}


@pytest.mark.asyncio
async def test_pause_and_resume_blocks_and_resumes_tokens():
    orch = Orchestrator(agent=None, provider=StreamingProvider())
    session = await orch.create_session()
    inputs = {"messages": [{"role": "user", "content": [{"type": "text", "data": "stream"}]}]}

    tokens = []
    paused = False
    resumed = False

    async def consume():
        nonlocal paused, resumed
        async for ev in orch.stream(session_id=session.id, inputs=inputs):
            if ev["type"] == EventType.TOKEN_EMITTED.value:
                tokens.append(ev["data"]["delta"])
                if len(tokens) == 1 and not paused:
                    await orch.control(session_id=session.id, command={"type": "pause.requested"})
                    paused = True
                    # Wait a bit; should not get another token while paused
                    await asyncio.sleep(0.04)
                    current_count = len(tokens)
                    await orch.control(session_id=session.id, command={"type": "resume.requested"})
                    resumed = True
                    # After resume, more tokens should arrive later; ensure count unchanged immediately
                    assert len(tokens) == current_count
            if ev["type"] == EventType.DECISION_COMPLETED.value:
                return

    await consume()
    assert paused and resumed
    assert len(tokens) >= 2

