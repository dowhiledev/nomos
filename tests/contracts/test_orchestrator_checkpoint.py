import pytest

from nomos.core import Orchestrator


class NoopProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {
            "type": "decision.completed",
            "data": {"action": "RESPOND", "response": "ok"},
        }


@pytest.mark.asyncio
async def test_checkpoint_control_creates_checkpoint_event():
    orch = Orchestrator(agent=None, provider=NoopProvider())
    session = await orch.create_session()
    await orch.control(
        session_id=session.id, command={"type": "checkpoint.requested", "id": "cpX"}
    )
    # Read one event from stream to confirm checkpoint
    got = False

    async def consume():
        nonlocal got
        async for ev in orch.stream(session_id=session.id):
            if ev.type == "checkpoint.created" and ev.data["id"] == "cpX":
                got = True
                return

    await consume()
    assert got
