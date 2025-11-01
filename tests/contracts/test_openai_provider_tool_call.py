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


class FakeOpenAIClientToolCall:
    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, *, model, messages, stream):  # noqa: ANN001
            assert stream is True
            # tool_call streamed over two chunks with partial JSON args
            d1 = _Delta([_ToolCallFn(0, name="web.search", arguments='{"query": "tokyo')])
            d2 = _Delta([_ToolCallFn(0, name="web.search", arguments='", "top_k": 1}')])
            return iter([_Chunk(d1), _Chunk(d2)])

    class _Chat:
        def __init__(self, parent):
            self.completions = FakeOpenAIClientToolCall._Completions(parent)

    def __init__(self):
        self.chat = FakeOpenAIClientToolCall._Chat(self)


@pytest.mark.asyncio
async def test_openai_provider_emits_tool_call_decision():
    provider = OpenAIProvider(model="gpt-4o-mini", client=FakeOpenAIClientToolCall())
    frames = []
    async for f in provider.stream_decision([{"role": "user", "content": [{"type": "text", "data": "hi"}]}], schema=None):
        frames.append(f)
    assert frames[-1]["data"]["action"] == "TOOL_CALL"
    call = frames[-1]["data"]["tool_call"]
    assert call["tool_name"] == "web.search"
    assert call["tool_kwargs"]["query"] == "tokyo"
    assert call["tool_kwargs"]["top_k"] == 1

