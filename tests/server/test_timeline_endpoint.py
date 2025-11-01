import pytest
from fastapi.testclient import TestClient

from nomos.server import create_app
from nomos.core import Orchestrator


class Provider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        # trivial immediate respond
        yield {"type": "decision.completed", "data": {"action": "RESPOND", "response": "ok"}}


@pytest.mark.asyncio
async def test_timeline_endpoint_lists_events():
    orch = Orchestrator(agent=None, provider=Provider())
    app = create_app(orchestrator=orch)
    client = TestClient(app)
    sid = client.post("/v2/sessions").json()["session_id"]
    client.post(
        f"/v2/sessions/{sid}/input",
        json={"messages": [{"role": "user", "content": [{"type": "text", "data": "hello"}]}]},
    )
    timeline = client.get(f"/v2/sessions/{sid}/timeline").json()
    types = [ev["type"] for ev in timeline["events"]]
    assert "session.created" in types
    assert "input.enqueued" in types

