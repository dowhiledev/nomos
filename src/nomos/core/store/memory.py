"""In-memory event store (dev/local) — skeleton."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List

from nomos.core.events import SessionEvent


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events: Dict[str, List[SessionEvent]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue[SessionEvent]] = defaultdict(
            asyncio.Queue
        )
        # per-session monotonically increasing event sequence for SSE ids
        self._seqs: Dict[str, int] = defaultdict(int)

    async def append(self, session_id: str, events: List[SessionEvent]) -> None:
        # assign event ids if not present to support SSE resume
        if session_id not in self._seqs:
            self._seqs[session_id] = 0
        if session_id not in self._events:
            self._events[session_id] = []
        if session_id not in self._queues:
            self._queues[session_id] = asyncio.Queue()
        for ev in events:
            if not ev.event_id:
                self._seqs[session_id] += 1
                ev.event_id = str(self._seqs[session_id])
        self._events[session_id].extend(events)
        for ev in events:
            await self._queues[session_id].put(ev)

    async def read_by_session(self, session_id: str) -> List[SessionEvent]:
        return list(self._events.get(session_id, []))

    async def _generator(self, session_id: str) -> AsyncIterator[SessionEvent]:
        q = self._queues[session_id]
        while True:
            ev = await q.get()
            yield ev

    def subscribe(self, session_id: str) -> AsyncIterator[SessionEvent]:
        return self._generator(session_id)


__all__ = ["InMemoryEventStore"]
