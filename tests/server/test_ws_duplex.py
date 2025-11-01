import json

import pytest
from fastapi.testclient import TestClient

from nomos.server import create_app
from nomos.core import Orchestrator


class FakeProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {"type": "io.token", "data": {"role": "assistant", "delta": "Hi"}}
        yield {"type": "decision.completed", "data": {"action": "RESPOND", "response": "Hi"}}


@pytest.mark.asyncio
async def test_ws_duplex_stream_and_input():
    orch = Orchestrator(agent=None, provider=FakeProvider())
    app = create_app(orchestrator=orch)
    client = TestClient(app)

    # create session via HTTP
    resp = client.post("/v2/sessions")
    sid = resp.json()["session_id"]

    with client.websocket_connect(f"/v2/sessions/{sid}/ws") as ws:
        # send an input message over WS
        ws.send_text(json.dumps({"type": "input", "payload": {"messages": [{"role": "user", "content": [{"type": "text", "data": "hello"}]}]}}))
        # receive a few events
        ev1 = json.loads(ws.receive_text())
        assert ev1["type"] in ("io.token", "decision.completed")

