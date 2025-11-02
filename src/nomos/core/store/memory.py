"""In-memory event store implementation (for development and testing).

This module provides a simple in-memory implementation of the EventStore protocol.
Events are stored in process memory and lost on restart. Suitable for:
- Development and prototyping
- Testing and unit tests
- Single-process deployments

For production use, implement EventStore with durable storage (PostgreSQL, etc).
"""

from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import AsyncIterator, Dict, List

from nomos.core.events import SessionEvent
from nomos.core.interfaces import EventStore


class InMemoryEventStore(EventStore):
    """In-memory append-only event store.

    Stores events for each session in memory. Provides:
    - Append-only semantics via list storage
    - Subscription support via asyncio.Queue
    - Automatic event ID assignment for SSE resume capability

    Events are organized per-session and maintain insertion order.
    All methods are async-compatible but all operations are synchronous
    (no I/O latency).

    Example:
        >>> store = InMemoryEventStore()
        >>> event = SessionEvent(
        ...     session_id="s1",
        ...     type=EventType.SESSION_CREATED,
        ...     data={}
        ... )
        >>> await store.append("s1", [event])
        >>> events = await store.read_by_session("s1")
        >>> async for ev in store.subscribe("s1"):
        ...     print(ev.type)
    """

    def __init__(self) -> None:
        """Initialize the in-memory event store.

        Sets up empty storage structures:
        - _events: Dict mapping session_id -> list of events
        - _queues: Dict mapping session_id -> subscription queue
        - _seqs: Dict mapping session_id -> event sequence number (for IDs)
        """
        self._events: Dict[str, List[SessionEvent]] = defaultdict(list)
        self._queues: Dict[str, asyncio.Queue[SessionEvent]] = defaultdict(
            asyncio.Queue
        )
        # per-session monotonically increasing event sequence for SSE ids
        self._seqs: Dict[str, int] = defaultdict(int)

    async def append(self, session_id: str, events: List[SessionEvent]) -> None:
        """Append events to a session's log.

        Atomically appends all events and:
        - Assigns event IDs if not present
        - Queues events for subscribers
        - Maintains session sequence numbers

        Args:
            session_id: Session identifier.
            events: List of SessionEvent objects to append.
        """
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
        """Read all events for a session.

        Args:
            session_id: Session identifier.

        Returns:
            List of all SessionEvent objects in append order.
        """
        return list(self._events.get(session_id, []))

    async def _generator(self, session_id: str) -> AsyncIterator[SessionEvent]:
        """Internal generator for subscription streaming.

        Args:
            session_id: Session identifier.

        Yields:
            SessionEvent objects as they are appended.
        """
        q = self._queues[session_id]
        while True:
            ev = await q.get()
            yield ev

    def subscribe(self, session_id: str) -> AsyncIterator[SessionEvent]:
        """Subscribe to a session's event stream.

        Returns an async iterator that yields events as they are appended.
        New subscriptions start receiving events after subscribe() is called
        (backfill is not provided; use read_by_session() for that).

        Args:
            session_id: Session identifier.

        Yields:
            SessionEvent objects as appended to the session.
        """
        return self._generator(session_id)


__all__ = ["InMemoryEventStore"]
