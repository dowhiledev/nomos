import types

import pytest

from nomos.llms.openai import OpenAI
from nomos.core.events import EventType
from nomos.core.schemas import Message, TextPart


class _Chunk:
    def __init__(self, content=None):
        self.choices = [
            types.SimpleNamespace(delta=types.SimpleNamespace(content=content))
        ]


class FakeOpenAIClient:
    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, *, model, messages, stream):  # noqa: ANN001
            assert stream is True
            # yield two token chunks and then nothing else
            return iter([_Chunk("Hello "), _Chunk("world")])

    class _Chat:
        def __init__(self, parent):
            self.completions = FakeOpenAIClient._Completions(parent)

    def __init__(self):
        self.chat = FakeOpenAIClient._Chat(self)


@pytest.mark.asyncio
async def test_openai_provider_stream_decision_with_fake_client():
    provider = OpenAI(model="gpt-4o-mini", client=FakeOpenAIClient())
    messages = [Message(role="user", content=[TextPart(type="text", data="hi")])]
    frames = []
    async for f in provider.stream_decision(messages, schema=None):
        frames.append(f)
    assert any(fr["type"] == EventType.TOKEN_EMITTED for fr in frames)
    assert frames[-1]["type"] == EventType.DECISION_COMPLETED
