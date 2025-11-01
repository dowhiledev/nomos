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
from .ports import LLMProviderPort


@dataclass
class _Session:
    id: str


class Orchestrator:
    def __init__(
        self,
        agent: Any,  # noqa: ANN401
        *,
        store: Optional[InMemoryEventStore] = None,
        provider: Optional[LLMProviderPort] = None,
    ) -> None:
        self._agent = agent
        self._store = store or InMemoryEventStore()
        self._provider = provider
        self._input_queues: Dict[str, asyncio.Queue[Dict[str, Any]]] = {}
        self._workers: Dict[str, asyncio.Task] = {}

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

    async def _worker(self, session_id: str) -> None:
        """Process queued inputs for a session using the provider (if available)."""
        q = self._input_queues[session_id]
        while True:
            payload = await q.get()
            try:
                # Start decision
                await self._store.append(
                    session_id,
                    [
                        SessionEvent(
                            session_id=session_id, type=EventType.DECISION_STARTED.value, data={}
                        ).model_dump(),
                    ],
                )
                if not self._provider:
                    # No provider wired: emit a trivial completion
                    await self._store.append(
                        session_id,
                        [
                            SessionEvent(
                                session_id=session_id,
                                type=EventType.DECISION_COMPLETED.value,
                                data={"action": "RESPOND", "response": "(provider not configured)"},
                            ).model_dump()
                        ],
                    )
                    continue

                # Stream decision from provider; provider yields generic frames
                async for frame in self._provider.stream_decision(payload.get("messages", []), schema=None):
                    ftype = frame.get("type")
                    if ftype == EventType.TOKEN_EMITTED.value:
                        await self._store.append(
                            session_id,
                            [
                                SessionEvent(
                                    session_id=session_id,
                                    type=EventType.TOKEN_EMITTED.value,
                                    data=frame.get("data", {}),
                                ).model_dump()
                            ],
                        )
                    elif ftype == EventType.DECISION_COMPLETED.value:
                        await self._store.append(
                            session_id,
                            [
                                SessionEvent(
                                    session_id=session_id,
                                    type=EventType.DECISION_COMPLETED.value,
                                    data=frame.get("data", {}),
                                ).model_dump()
                            ],
                        )
                        break
            except Exception as exc:  # noqa: BLE001
                await self._store.append(
                    session_id,
                    [
                        SessionEvent(
                            session_id=session_id,
                            type=EventType.ERROR_OCCURRED.value,
                            data={"message": str(exc)},
                        ).model_dump()
                    ],
                )

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

        # Ensure a worker is running for this session to process queued inputs
        if session_id not in self._workers:
            self._workers[session_id] = asyncio.create_task(self._worker(session_id))

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
