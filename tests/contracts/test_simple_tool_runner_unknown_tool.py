import pytest

from nomos.tools.runner import SimpleToolRunner


@pytest.mark.asyncio
async def test_simple_tool_runner_unknown_tool_yields_error():
    runner = SimpleToolRunner({})
    frames = []
    async for frame in runner.run("missing", {}, {}):
        frames.append(frame)
    assert frames[-1]["type"] == "tool.error"
    assert frames[-1]["error"] == "unknown tool"
