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

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from nomos.core import Orchestrator
from nomos.graph import AgentSpec


def create_app(agent: Optional[AgentSpec] = None, *, orchestrator: Optional[Orchestrator] = None) -> FastAPI:
    orch = orchestrator or Orchestrator(agent=agent)

    app = FastAPI(title="Nomos vNext Server", version="0.1.0")

    @app.post("/v2/sessions")
    async def create_session() -> Dict[str, Any]:  # noqa: ANN401
        s = await orch.create_session()
        return {"session_id": s.id}

    @app.post("/v2/sessions/{sid}/input")
    async def post_input(sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        await orch.input(session_id=sid, inputs=payload)
        return {"ok": True}

    @app.post("/v2/sessions/{sid}/control")
    async def post_control(sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        await orch.control(session_id=sid, command=payload)
        return {"ok": True}

    @app.get("/v2/sessions/{sid}/state")
    async def get_state(sid: str) -> Dict[str, Any]:  # noqa: ANN401
        return await orch.materialize_state(session_id=sid)

    async def _sse_gen(sid: str) -> AsyncIterator[str]:
        async for ev in orch.stream(session_id=sid):
            yield f"data: {json.dumps(ev)}\n\n"

    @app.get("/v2/sessions/{sid}/events")
    async def sse(sid: str) -> StreamingResponse:  # noqa: ANN401
        return StreamingResponse(_sse_gen(sid), media_type="text/event-stream")

    @app.websocket("/v2/sessions/{sid}/ws")
    async def ws_endpoint(ws: WebSocket, sid: str) -> None:
        await ws.accept()

        async def send_events() -> None:
            async for ev in orch.stream(session_id=sid):
                await ws.send_text(json.dumps(ev))

        sender = asyncio.create_task(send_events())
        try:
            while True:
                msg_text = await ws.receive_text()
                try:
                    msg = json.loads(msg_text)
                except Exception:
                    await ws.send_text(json.dumps({"type": "error", "message": "invalid json"}))
                    continue
                mtype = msg.get("type")
                if mtype == "input":
                    await orch.input(session_id=sid, inputs=msg.get("payload", {}))
                elif mtype == "control":
                    await orch.control(session_id=sid, command=msg.get("payload", {}))
                else:
                    await ws.send_text(json.dumps({"type": "error", "message": "unknown message type"}))
        except WebSocketDisconnect:
            sender.cancel()
        except Exception:
            sender.cancel()
            raise

    return app


__all__ = ["create_app"]

