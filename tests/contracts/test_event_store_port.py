import asyncio
import pytest

from nomos.core.store.memory import InMemoryEventStore


@pytest.mark.asyncio
async def test_event_store_append_and_subscribe():
    store = InMemoryEventStore()
    session_id = "s1"

    async def producer():
        await asyncio.sleep(0.01)
        await store.append(session_id, [{"type": "x", "data": {"i": 1}}])
        await asyncio.sleep(0.01)
        await store.append(session_id, [{"type": "y", "data": {"i": 2}}])

    async def consumer():
        events = []
        async for ev in store.subscribe(session_id):
            events.append(ev)
            if len(events) == 2:
                return events

    results = await asyncio.gather(producer(), consumer())
    # results[1] contains collected events from consumer
    collected = results[1]
    assert collected[0]["type"] == "x"
    assert collected[1]["type"] == "y"
