import json
import threading
import time

import pytest
from fastapi.testclient import TestClient

from nomos.server import create_app
from nomos.core import Orchestrator


class FakeProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {"type": "io.token", "data": {"role": "assistant", "delta": "Hi"}}
        yield {"type": "decision.completed", "data": {"action": "RESPOND", "response": "Hi"}}


@pytest.mark.skip(reason="SSE streaming with TestClient is unstable; WS covers duplex streaming")
@pytest.mark.asyncio
async def test_sse_stream_emits_events_on_input():
    orch = Orchestrator(agent=None, provider=FakeProvider())
    app = create_app(orchestrator=orch)
    client = TestClient(app)

    sid = client.post("/v2/sessions").json()["session_id"]
    # enqueue input before opening SSE; worker auto-starts on input
    client.post(
        f"/v2/sessions/{sid}/input",
        json={"messages": [{"role": "user", "content": [{"type": "text", "data": "hello"}]}]},
    )

    with client.stream("GET", f"/v2/sessions/{sid}/events") as s:
        # read a couple of lines and ensure we get a data event
        got = False
        for line in s.iter_lines():
            if not line:
                continue
            if line.startswith("data: "):
                ev = json.loads(line.split("data: ", 1)[1])
                assert ev["type"] in ("io.token", "decision.completed")
                got = True
                break
        assert got
