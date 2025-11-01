import pytest

from nomos.core import Orchestrator


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
        if isinstance(out.get("data"), dict) and "password" in out["data"]:
            out["data"]["password"] = "***"
        return out

    orch = Orchestrator(agent=None, provider=Provider(), redact=redact)
    session = await orch.create_session()
    await orch.input(
        session_id=session.id,
        inputs={
            "messages": [{"role": "user", "content": [{"type": "text", "data": "hi"}]}],
            "password": "secret123",
        },
    )
    events = await orch.list_events(session_id=session.id)
    # input.enqueued event should have password masked
    masked = [e for e in events if e["type"] == "input.enqueued"][0]
    assert masked["data"].get("password") == "***"
