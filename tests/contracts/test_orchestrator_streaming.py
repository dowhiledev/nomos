import asyncio
from typing import Any, AsyncIterator, Dict, List

import pytest

from nomos.core import Orchestrator
from nomos.core.events import EventType


class FakeProvider:
    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "Hello "},
        }
        await asyncio.sleep(0.005)
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "world"},
        }
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": "Hello world"},
        }


@pytest.mark.asyncio
async def test_orchestrator_streams_provider_events():
    orch = Orchestrator(agent=None, provider=FakeProvider())
    session = await orch.create_session()

    inputs = {
        "messages": [{"role": "user", "content": [{"type": "text", "data": "hi"}]}]
    }

    tokens = []
    decision = None

    async def consume():
        async for ev in orch.stream(session_id=session.id, inputs=inputs):
            if ev["type"] == EventType.TOKEN_EMITTED.value:
                tokens.append(ev["data"]["delta"])
            if ev["type"] == EventType.DECISION_COMPLETED.value:
                nonlocal decision
                decision = ev["data"]
                return

    await consume()
    assert tokens
    assert decision and decision.get("action") == "RESPOND"
