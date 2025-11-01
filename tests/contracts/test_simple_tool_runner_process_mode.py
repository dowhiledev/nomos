import pytest

from nomos.tools.runner import SimpleToolRunner


def add(a: int, b: int) -> int:
    return a + b


@pytest.mark.asyncio
async def test_simple_tool_runner_process_mode_sync_fn():
    runner = SimpleToolRunner({"add": add}, execution_mode="process", processes=1)
    frames = []
    async for f in runner.run("add", {"a": 2, "b": 3}, {}):
        frames.append(f)
    assert frames[0]["type"] == "tool.started"
    assert frames[-1]["type"] == "tool.completed"
    assert frames[-1]["result"] == 5
