import asyncio
import pytest

from nomos.tools.runner import SimpleToolRunner


async def bad_tool():
    # Yield an invalid frame type
    yield {"type": "tool.weird", "x": 1}
    await asyncio.sleep(0)
    yield {"type": "tool.completed", "result": True}


@pytest.mark.asyncio
async def test_tool_runner_validates_frames_and_maps_unknown_to_error():
    runner = SimpleToolRunner({"bad": bad_tool})
    frames = []
    async for f in runner.run("bad", {}, {}):
        frames.append(f)
        if f["type"] == "tool.completed":
            break
    types = [f["type"] for f in frames]
    assert "tool.error" in types  # invalid mapped to error
    assert types[-1] == "tool.completed"
