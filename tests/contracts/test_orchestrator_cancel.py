import asyncio
import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType


class SlowTokenProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        # Emit multiple tokens slowly; never completes unless not cancelled
        for ch in ["H", "e", "l", "l", "o"]:
            await asyncio.sleep(0.01)
            yield {
                "type": EventType.TOKEN_EMITTED.value,
                "data": {"role": "assistant", "delta": ch},
            }
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": "Hello"},
        }


@pytest.mark.asyncio
async def test_cancel_mid_tokens():
    orch = Orchestrator(agent=None, provider=SlowTokenProvider())
    session = await orch.create_session()
    inputs = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "data": "say hello"}]}
        ]
    }

    tokens = []
    cancel_sent = False

    async def consume():
        async for ev in orch.stream(session_id=session.id, inputs=inputs):
            if ev.type == EventType.TOKEN_EMITTED:
                tokens.append(ev.data["delta"])
                nonlocal cancel_sent
                if not cancel_sent:
                    await orch.control(
                        session_id=session.id, command={"type": "cancel.requested"}
                    )
                    cancel_sent = True
            if ev.type == EventType.CANCEL_APPLIED:
                return

    await consume()
    assert tokens  # at least one token before cancel
