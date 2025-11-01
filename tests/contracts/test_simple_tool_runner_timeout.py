import asyncio
import pytest

from nomos.tools.runner import SimpleToolRunner


async def slow_frame_tool():
    # wait longer than timeout before first yield
    await asyncio.sleep(0.02)
    yield {"type": "tool.completed", "result": True}


@pytest.mark.asyncio
async def test_simple_tool_runner_timeout_errors():
    runner = SimpleToolRunner({"slow": slow_frame_tool}, timeout_s=0.005)
    frames = []
    async for frame in runner.run("slow", {}, {}):
        frames.append(frame)
        if frame["type"] in ("tool.completed", "tool.error"):
            break
    # second frame should be an error due to timeout
    assert frames[0]["type"] == "tool.started"
    assert frames[-1]["type"] == "tool.error"
    assert frames[-1]["error"] == "timeout"
