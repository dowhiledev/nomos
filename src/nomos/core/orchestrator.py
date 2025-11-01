"""Session orchestrator (actor) — skeleton.

Implements the minimal API used by the examples:
- create_session() -> returns an object with .id
- stream(session_id, inputs=None) -> async iterator of SessionEvents (dicts)
- input(session_id, inputs) -> enqueue user messages
- control(session_id, command) -> apply control (pause/resume/cancel/checkpoint)
- materialize_state(session_id) -> SessionState (dict)

This is a simplified first pass to enable incremental development; real decision/tool execution
will be added as LLMProvider/ToolRunner adapters become available.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, Optional

from .events import EventType, SessionEvent
from .state import SessionState
from .store.memory import InMemoryEventStore


@dataclass
class _Session:
    id: str


class Orchestrator:
    def __init__(self, agent: Any, *, store: Optional[InMemoryEventStore] = None) -> None:  # noqa: ANN401
        self._agent = agent
        self._store = store or InMemoryEventStore()
        self._input_queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}

    async def create_session(self) -> _Session:
        sid = str(uuid.uuid4())
        self._input_queues[sid] = asyncio.Queue()
        await self._store.append(
            sid,
            [
                SessionEvent(session_id=sid, type=EventType.SESSION_CREATED.value, data={}).model_dump(),
            ],
        )
        return _Session(id=sid)

    async def input(self, session_id: str, inputs: Dict[str, Any]) -> None:  # noqa: ANN401
        await self._store.append(
            session_id,
            [
                SessionEvent(
                    session_id=session_id, type=EventType.INPUT_ENQUEUED.value, data=inputs
                ).model_dump(),
            ],
        )
        await self._input_queues[session_id].put(inputs)

    async def control(self, session_id: str, command: Dict[str, Any]) -> None:  # noqa: ANN401
        await self._store.append(
            session_id,
            [
                SessionEvent(
                    session_id=session_id, type=EventType.CONTROL_APPLIED.value, data=command
                ).model_dump(),
            ],
        )

    async def stream(
        self, session_id: str, inputs: Optional[Dict[str, Any]] = None  # noqa: ANN401
    ) -> AsyncIterator[Dict[str, Any]]:
        # If initial inputs provided, enqueue them first
        if inputs:
            await self.input(session_id, inputs)

        # For now, just forward events appended to the store (including inputs/controls)
        async for ev in self._store.subscribe(session_id):
            yield ev

    async def materialize_state(self, session_id: str) -> Dict[str, Any]:  # noqa: ANN401
        events = await self._store.read_by_session(session_id)
        state = SessionState(session_id=session_id)
        # A minimal projection: track last action/token and maintain a small tail
        tail = []
        for ev in events[-50:]:
            tail.append(ev)
            if ev["type"] == EventType.DECISION_COMPLETED.value:
                state.last_action = "decision.completed"
            if ev["type"] == EventType.TOKEN_EMITTED.value:
                state.last_action = "io.token"
        state.history_tail = tail
        return state.model_dump()

