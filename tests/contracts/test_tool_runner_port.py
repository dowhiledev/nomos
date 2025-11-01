import asyncio
from typing import Any, AsyncIterator, Dict

import pytest


class FakeToolRunner:
    async def run(self, tool_name: str, args: Dict[str, Any], ctx: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        yield {"type": "tool.started", "tool": tool_name}
        await asyncio.sleep(0.01)
        yield {"type": "tool.progress", "stage": "step1"}
        await asyncio.sleep(0.01)
        yield {"type": "tool.completed", "result": {"ok": True}}


@pytest.mark.asyncio
async def test_tool_runner_contract():
    runner = FakeToolRunner()
    frames = []
    async for frame in runner.run("web.search", {"query": "tokyo"}, {}):
        frames.append(frame)
    assert frames[0]["type"] == "tool.started"
    assert frames[-1]["type"] == "tool.completed"

