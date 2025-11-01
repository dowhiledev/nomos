"""In-memory event store (dev/local) — skeleton."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = defaultdict(
            asyncio.Queue
        )
        # per-session monotonically increasing event sequence for SSE ids
        self._seqs: Dict[str, int] = defaultdict(int)

    async def append(self, session_id: str, events: List[Dict[str, Any]]) -> None:
        # assign event ids if not present to support SSE resume
        for ev in events:
            if not ev.get("event_id"):
                self._seqs[session_id] += 1
                ev["event_id"] = str(self._seqs[session_id])
        self._events[session_id].extend(events)
        for ev in events:
            await self._queues[session_id].put(ev)

    async def read_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        return list(self._events.get(session_id, []))

    async def _generator(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        q = self._queues[session_id]
        while True:
            ev = await q.get()
            yield ev

    def subscribe(self, session_id: str) -> AsyncIterator[Dict[str, Any]]:
        return self._generator(session_id)


__all__ = ["InMemoryEventStore"]
