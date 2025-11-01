import asyncio
import pytest

from nomos.tools.decorators import tool, registry_from_tools
from nomos.tools.runner import SimpleToolRunner


@tool(name="decorated.echo", timeout_s=0.01)
async def echo(text: str):
    await asyncio.sleep(0)
    return text


@pytest.mark.asyncio
async def test_tool_decorator_registry_and_runner_acl():
    reg = registry_from_tools(echo)
    # unauthorized by default when allowed_tools is set and name not included
    runner = SimpleToolRunner(reg, allowed_tools={"other"})
    frames = []
    async for f in runner.run("decorated.echo", {"text": "hi"}, {}):
        frames.append(f)
    assert frames[-1]["type"] == "tool.error"
    assert frames[-1]["error"] == "unauthorized"

    # allow the tool and ensure it completes
    runner = SimpleToolRunner(reg, allowed_tools={"decorated.echo"})
    frames = []
    async for f in runner.run("decorated.echo", {"text": "hi"}, {}):
        frames.append(f)
    assert frames[0]["type"] == "tool.started"
    assert frames[-1]["type"] == "tool.completed"
    assert frames[-1]["result"] == "hi"
