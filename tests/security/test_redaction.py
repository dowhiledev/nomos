import pytest

from nomos.core import Orchestrator
from nomos.core.schemas import SessionInput


class Provider:
    async def stream_decision(self, messages, schema):  # type: ignore[no-untyped-def]
        yield {
            "type": "decision.completed",
            "data": {"action": "RESPOND", "response": "ok"},
        }


@pytest.mark.asyncio
async def test_event_redaction_masks_sensitive_fields():
    def redact(ev: dict) -> dict:  # noqa: ANN001
        # mask any 'password' keys inside data
        out = dict(ev)
        if "password" in out:
            out["password"] = "***"
        return out

    orch = Orchestrator(agent=None, provider=Provider(), redact=redact)
    session = await orch.create_session()
    await orch.input(
        session_id=session.id,
        inputs=SessionInput(
            messages=[{"role": "user", "content": [{"type": "text", "data": "hi"}]}],
            schema=None,
            password="secret123",
        ),
    )
    events = await orch.list_events(session_id=session.id)
    # input.enqueued event should have password masked
    masked = [e for e in events if e.type == "input.enqueued"][0]
    assert masked.data.get("password") == "***"
