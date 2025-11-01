import asyncio
import pytest

from nomos.tools.runner import SimpleToolRunner


async def echo_tool(text: str):
    yield {"type": "tool.progress", "stage": "echoing"}
    await asyncio.sleep(0.001)
    yield {"type": "tool.completed", "result": text}


@pytest.mark.asyncio
async def test_simple_tool_runner_streams_frames():
    runner = SimpleToolRunner({"echo": echo_tool})
    frames = []
    async for frame in runner.run("echo", {"text": "hello"}, {}):
        frames.append(frame)
    assert frames[0]["type"] == "tool.started"
    assert any(f["type"] == "tool.progress" for f in frames)
    assert frames[-1]["type"] == "tool.completed"
