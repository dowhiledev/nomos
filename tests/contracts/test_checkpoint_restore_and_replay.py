import pytest

from nomos.core import Orchestrator
from nomos.core.replay import project_state


class NoopProvider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {
            "type": "decision.completed",
            "data": {"action": "RESPOND", "response": "ok"},
        }


@pytest.mark.asyncio
async def test_checkpoint_restore_and_replay_projection():
    orch = Orchestrator(agent=None, provider=NoopProvider())
    session = await orch.create_session()
    # checkpoint created at initial node (None)
    await orch.control(
        session_id=session.id, command={"type": "checkpoint.requested", "id": "cp1"}
    )
    # restore checkpoint
    await orch.control(
        session_id=session.id, command={"type": "checkpoint.restore", "id": "cp1"}
    )

    # materialized state
    st = await orch.materialize_state(session_id=session.id)
    # replayed state from event log
    events = await orch._store.read_by_session(session.id)  # type: ignore[attr-defined]
    st2 = project_state(session.id, events)
    assert st["current_node"] == st2["current_node"]
