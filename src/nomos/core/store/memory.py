"""In-memory event store (dev/local) — skeleton."""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator, Dict, List


class InMemoryEventStore:
    def __init__(self) -> None:
        self._events: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = defaultdict(asyncio.Queue)

    async def append(self, session_id: str, events: List[Dict[str, Any]]) -> None:
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

