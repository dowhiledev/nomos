import types
import pytest

from nomos.llms.openai_provider import OpenAIProvider
from nomos.core.events import EventType


class CapturingClient:
    def __init__(self):
        self.captured_messages = None
        self.chat = CapturingClient._Chat(self)

    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, *, model, messages, stream):  # noqa: ANN001
            self._parent.captured_messages = messages
            # yield one content token and finish
            return iter(
                [
                    types.SimpleNamespace(
                        choices=[
                            types.SimpleNamespace(
                                delta=types.SimpleNamespace(content="hello")
                            )
                        ]
                    )
                ]
            )

    class _Chat:
        def __init__(self, parent):
            self.completions = CapturingClient._Completions(parent)

    # __init__ provided on outer class


@pytest.mark.asyncio
async def test_openai_provider_maps_content_parts():
    client = CapturingClient()
    provider = OpenAIProvider(client=client)
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "text", "data": "hi"},
                {"type": "image", "data": {"url": "https://x/y.jpg"}},
            ],
        }
    ]
    frames = []
    async for f in provider.stream_decision(messages, schema=None):
        frames.append(f)
    assert any(fr["type"] == EventType.TOKEN_EMITTED.value for fr in frames)
    # verify mapped message shape used for OpenAI call
    assert isinstance(client.captured_messages, list)
    content = client.captured_messages[0]["content"]
    assert any(part["type"] == "text" for part in content)
    assert any(part["type"] == "image_url" for part in content)
