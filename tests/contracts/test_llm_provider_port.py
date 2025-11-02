import asyncio
from typing import Any, AsyncIterator, Dict, List

import pytest

from nomos.core.events import EventType


class FakeProvider:
    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Emit two token frames then a final decision frame
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "Hello "},
        }
        await asyncio.sleep(0.01)
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "world!"},
        }
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": "Hello world!"},
        }

    async def stream_generate(
        self, messages: List[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        yield {
            "type": EventType.TOKEN_EMITTED.value,
            "data": {"role": "assistant", "delta": "Hi"},
        }


@pytest.mark.asyncio
async def test_llm_provider_contract():
    provider = FakeProvider()
    frames = []
    async for frame in provider.stream_decision(
        [{"role": "user", "content": [{"type": "text", "data": "hi"}]}], schema=None
    ):
        frames.append(frame)
    assert frames[-1]["type"] == EventType.DECISION_COMPLETED
    assert frames[0]["type"] == EventType.TOKEN_EMITTED
