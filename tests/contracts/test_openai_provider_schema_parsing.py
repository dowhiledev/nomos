import types
import pytest
from pydantic import BaseModel

from nomos.llms.openai import OpenAI


class _Chunk:
    def __init__(self, content=None):
        self.choices = [
            types.SimpleNamespace(delta=types.SimpleNamespace(content=content))
        ]


class FakeTextClient:
    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, *, model, messages, stream):  # noqa: ANN001
            assert stream is True
            # yield JSON over two chunks
            return iter([_Chunk('{"foo":'), _Chunk("1}")])

    class _Chat:
        def __init__(self, parent):
            self.completions = FakeTextClient._Completions(parent)

    def __init__(self):
        self.chat = FakeTextClient._Chat(self)


class FooSchema(BaseModel):
    foo: int


@pytest.mark.asyncio
async def test_openai_provider_parses_schema_for_respond():
    provider = OpenAI(client=FakeTextClient())
    frames = []
    async for f in provider.stream_decision(
        [{"role": "user", "content": [{"type": "text", "data": "hi"}]}],
        schema=FooSchema,
    ):
        frames.append(f)
    decision = frames[-1]
    assert decision["data"]["action"] == "RESPOND"
    assert decision["data"]["parsed"]["foo"] == 1


class _Delta:
    def __init__(self, tool_calls):
        self.tool_calls = tool_calls


class _ToolCallFn:
    def __init__(self, index, name=None, arguments=None):
        self.index = index
        self.function = types.SimpleNamespace(name=name, arguments=arguments)


class _ChunkTC:
    def __init__(self, delta):
        self.choices = [types.SimpleNamespace(delta=delta)]


class FakeToolClient:
    class _Completions:
        def __init__(self, parent):
            self._parent = parent

        def create(self, *, model, messages, stream):  # noqa: ANN001
            assert stream is True
            d1 = _Delta(
                [_ToolCallFn(0, name="web.search", arguments='{"query": "tokyo')]
            )
            d2 = _Delta([_ToolCallFn(0, name="web.search", arguments='", "top_k": 1}')])
            return iter([_ChunkTC(d1), _ChunkTC(d2)])

    class _Chat:
        def __init__(self, parent):
            self.completions = FakeToolClient._Completions(parent)

    def __init__(self):
        self.chat = FakeToolClient._Chat(self)


class SearchArgs(BaseModel):
    query: str
    top_k: int


@pytest.mark.asyncio
async def test_openai_provider_parses_tool_kwargs_schema():
    provider = OpenAI(client=FakeToolClient())
    schema = {"web.search": SearchArgs}
    frames = []
    async for f in provider.stream_decision(
        [{"role": "user", "content": [{"type": "text", "data": "hi"}]}], schema=schema
    ):
        frames.append(f)
    decision = frames[-1]
    call = decision["data"]["tool_call"]
    assert call["tool_kwargs_parsed"]["query"] == "tokyo"
    assert call["tool_kwargs_parsed"]["top_k"] == 1
