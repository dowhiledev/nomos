"""Nomos server factory (FastAPI) — SSE + WS transport.

This transport is optional and kept thin over the core orchestrator.
Endpoints (prefix /v2):
- POST /sessions -> {session_id}
- POST /sessions/{id}/input -> ack
- POST /sessions/{id}/control -> ack
- GET  /sessions/{id}/state -> materialized state
- GET  /sessions/{id}/events -> SSE stream of events
- WS   /sessions/{id}/ws -> duplex: send events to client; receive inputs/controls
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator, Dict, Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import StreamingResponse

from nomos.core import Orchestrator
from nomos.core.observe import metrics_snapshot
from nomos.core.schemas import SessionInput, ControlCommand
from nomos.core.state import SessionState
from nomos.core.events import SessionEvent
from nomos.graph import AgentSpec


def create_app(
    agent: Optional[AgentSpec] = None, *, orchestrator: Optional[Orchestrator] = None
) -> FastAPI:
    orch = orchestrator or Orchestrator(agent=agent)

    app = FastAPI(title="Nomos vNext Server", version="0.1.0")

    @app.post("/v2/sessions")
    async def create_session() -> Dict[str, Any]:  # noqa: ANN401
        s = await orch.create_session()
        return {"session_id": s.id}

    @app.post("/v2/sessions/{sid}/input")
    async def post_input(sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        inputs = SessionInput.model_validate(payload)
        await orch.input(session_id=sid, inputs=inputs)
        return {"ok": True}

    @app.post("/v2/sessions/{sid}/control")
    async def post_control(sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        command = ControlCommand.model_validate(payload)
        await orch.control(session_id=sid, command=command)
        return {"ok": True}

    @app.get("/v2/sessions/{sid}/state")
    async def get_state(sid: str) -> Dict[str, Any]:  # noqa: ANN401
        state = await orch.materialize_state(session_id=sid)
        return state.model_dump()

    @app.get("/v2/sessions/{sid}/timeline")
    async def get_timeline(sid: str) -> Dict[str, Any]:  # noqa: ANN401
        events = await orch.list_events(session_id=sid)
        return {"session_id": sid, "events": [e.model_dump() for e in events]}

    @app.get("/v2/metrics")
    async def get_metrics() -> Dict[str, Any]:  # noqa: ANN401
        return metrics_snapshot()

    async def _sse_gen(
        sid: str, last_event_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        # Yield existing timeline first (after last_event_id if provided)
        try:
            existing = await orch.list_events(session_id=sid)
        except Exception:
            existing = []
        # filter by last_event_id if present
        if last_event_id is not None:

            def _after(eid: Optional[str]) -> bool:
                try:
                    return int((eid or "0")) > int(last_event_id)
                except Exception:
                    return True

            existing = [ev for ev in existing if _after(ev.event_id)]
        for event in existing:
            if ev_id := event.event_id:
                yield f"id: {ev_id}\n"
            yield f"data: {json.dumps(event.model_dump())}\n\n"
        # Then stream new events
        async for ev in orch.stream(session_id=sid):
            if ev_id := ev.event_id:
                yield f"id: {ev_id}\n"
            yield f"data: {json.dumps(ev.model_dump())}\n\n"

    @app.get("/v2/sessions/{sid}/events")
    async def sse(sid: str, request: Request) -> StreamingResponse:  # noqa: ANN401
        # Support SSE resume via Last-Event-ID
        last_id = request.headers.get("last-event-id") or request.headers.get(
            "Last-Event-ID"
        )
        return StreamingResponse(
            _sse_gen(sid, last_event_id=last_id), media_type="text/event-stream"
        )

    @app.websocket("/v2/sessions/{sid}/ws")
    async def ws_endpoint(ws: WebSocket, sid: str) -> None:
        await ws.accept()

        async def send_events() -> None:
            async for ev in orch.stream(session_id=sid):
                await ws.send_text(json.dumps(ev.model_dump()))

        sender = asyncio.create_task(send_events())
        try:
            while True:
                msg_text = await ws.receive_text()
                try:
                    msg = json.loads(msg_text)
                except Exception:
                    await ws.send_text(
                        json.dumps({"type": "error", "message": "invalid json"})
                    )
                    continue
                mtype = msg.get("type")
                if mtype == "input":
                    await orch.input(session_id=sid, inputs=msg.get("payload", {}))
                elif mtype == "control":
                    await orch.control(session_id=sid, command=msg.get("payload", {}))
                else:
                    await ws.send_text(
                        json.dumps({"type": "error", "message": "unknown message type"})
                    )
        except WebSocketDisconnect:
            sender.cancel()
        except Exception:
            sender.cancel()
            raise

    return app


__all__ = ["create_app", "SessionState", "SessionEvent"]
