import types
import pytest

from nomos.llms.openai_provider import OpenAIProvider


class _Delta:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class _ToolCallFn:
    def __init__(self, index, name=None, arguments=None):
        self.index = index
        self.function = types.SimpleNamespace(name=name, arguments=arguments)


class _Chunk:
    def __init__(self, delta):
        self.choices = [types.SimpleNamespace(delta=delta)]


class FakeOpenAIClientMalformed:
    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, *, model, messages, stream):  # noqa: ANN001
            assert stream is True
            # malformed JSON across chunks
            d1 = _Delta(
                [_ToolCallFn(0, name="web.search", arguments='{"query": "tokyo')]
            )
            d2 = _Delta([_ToolCallFn(0, name="web.search", arguments='"')])
            return iter([_Chunk(d1), _Chunk(d2)])

    class _Chat:
        def __init__(self, parent):
            self.completions = FakeOpenAIClientMalformed._Completions(parent)

    def __init__(self):
        self.chat = FakeOpenAIClientMalformed._Chat(self)


@pytest.mark.asyncio
async def test_openai_provider_tool_call_malformed_args_raw_fallback():
    provider = OpenAIProvider(model="gpt-4o-mini", client=FakeOpenAIClientMalformed())
    frames = []
    async for f in provider.stream_decision(
        [{"role": "user", "content": [{"type": "text", "data": "hi"}]}], schema=None
    ):
        frames.append(f)
    call = frames[-1]["data"]["tool_call"]
    assert call["tool_name"] == "web.search"
    assert "__raw__" in call["tool_kwargs"]
