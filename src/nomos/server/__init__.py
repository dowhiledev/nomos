"""Nomos server factory (FastAPI) — SSE + WS transport layer.

This optional transport layer provides RESTful and WebSocket APIs over the core
orchestrator. It is designed to be thin and stateless, delegating all logic to the
core orchestrator.

The API prefix is `/v2` and includes:

**Session Management:**
- `POST /v2/sessions`: Create a new session
- `POST /v2/sessions/{id}/input`: Send inputs to a session
- `POST /v2/sessions/{id}/control`: Send control commands (pause, resume, cancel)

**State & Events:**
- `GET /v2/sessions/{id}/state`: Fetch materialized session state
- `GET /v2/sessions/{id}/timeline`: Fetch complete event timeline
- `GET /v2/sessions/{id}/events`: SSE stream (supports Last-Event-ID for resume)

**Metrics:**
- `GET /v2/metrics`: Fetch aggregated metrics snapshot

**WebSocket:**
- `WS /v2/sessions/{id}/ws`: Duplex stream for real-time events and input/control

All endpoints use JSON payloads and return JSON responses. The SSE endpoint
supports standard HTTP resumption via Last-Event-ID headers.

Example:
    >>> from nomos.server import create_app
    >>> from nomos.graph import AgentSpec
    >>> spec = AgentSpec(...)
    >>> app = create_app(agent=spec)
    >>> # Run with: uvicorn app:app --reload
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
    """Create a FastAPI application for orchestrator transport.
    
    Constructs a stateless FastAPI app that wraps the given orchestrator,
    exposing its functionality via REST/WS endpoints. Useful for deploying
    Nomos agents as microservices.
    
    Args:
        agent: Optional AgentSpec to compile into a new orchestrator.
            Ignored if orchestrator is provided.
        orchestrator: Optional pre-built Orchestrator instance. If not provided,
            creates one from the agent spec.
    
    Returns:
        FastAPI application instance ready to run or mount.
    
    Raises:
        ValueError: If neither agent nor orchestrator is provided.
    
    Example:
        >>> from nomos.graph import GraphBuilder
        >>> from nomos.server import create_app
        >>> builder = GraphBuilder()
        >>> builder.node("start", prompt="What is your name?")
        >>> spec = builder.compile()
        >>> app = create_app(agent=spec)
    """
    orch = orchestrator or Orchestrator(agent=agent)

    app = FastAPI(title="Nomos vNext Server", version="0.1.0")

    @app.post("/v2/sessions")
    async def create_session() -> Dict[str, Any]:  # noqa: ANN401
        """Create a new orchestrator session.
        
        Initializes a fresh session with empty event log and state. Returns
        the session ID for use in subsequent requests.
        
        Returns:
            JSON object with 'session_id' string.
        
        Example:
            >>> # POST /v2/sessions
            >>> # Response: {"session_id": "abc123"}
        """
        s = await orch.create_session()
        return {"session_id": s.id}

    @app.post("/v2/sessions/{sid}/input")
    async def post_input(sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        """Send user input to a session.
        
        Delivers user input messages to an active session. The orchestrator will
        process the input, run decision steps, and emit events.
        
        Args:
            sid: Session ID from create_session.
            payload: SessionInput payload containing messages and metadata.
                Expected shape: {"messages": [{"role": "user", "content": "..."}]}
        
        Returns:
            JSON object with 'ok': true on success.
        
        Raises:
            422: If payload does not match SessionInput schema.
            404: If session not found.
        
        Example:
            >>> # POST /v2/sessions/abc123/input
            >>> # Payload: {"messages": [{"role": "user", "content": "Hello"}]}
            >>> # Response: {"ok": true}
        """
        inputs = SessionInput.model_validate(payload)
        await orch.input(session_id=sid, inputs=inputs)
        return {"ok": True}

    @app.post("/v2/sessions/{sid}/control")
    async def post_control(sid: str, payload: Dict[str, Any]) -> Dict[str, Any]:  # noqa: ANN401
        """Send control commands to a session.
        
        Sends control signals to an active session (pause, resume, cancel).
        Used to interrupt or manage long-running orchestrations.
        
        Args:
            sid: Session ID from create_session.
            payload: ControlCommand payload.
                Expected shape: {"command": "pause" | "resume" | "cancel"}
        
        Returns:
            JSON object with 'ok': true on success.
        
        Raises:
            422: If payload does not match ControlCommand schema.
            404: If session not found.
        
        Example:
            >>> # POST /v2/sessions/abc123/control
            >>> # Payload: {"command": "pause"}
            >>> # Response: {"ok": true}
        """
        command = ControlCommand.model_validate(payload)
        await orch.control(session_id=sid, command=command)
        return {"ok": True}

    @app.get("/v2/sessions/{sid}/state")
    async def get_state(sid: str) -> Dict[str, Any]:  # noqa: ANN401
        """Fetch materialized session state.
        
        Returns the computed state of a session, including current node,
        message history, and decision history (last 10 actions).
        
        This is a point-in-time snapshot; use /events for a full timeline.
        
        Args:
            sid: Session ID from create_session.
        
        Returns:
            SessionState serialized as JSON.
        
        Raises:
            404: If session not found.
        
        Example:
            >>> # GET /v2/sessions/abc123/state
            >>> # Response:
            >>> # {
            >>> #   "session_id": "abc123",
            >>> #   "current_node": "start",
            >>> #   "last_action": {"action": "RESPOND", "response": "Hi!"},
            >>> #   "messages": [{"role": "user", "content": "Hello"}],
            >>> #   ...
            >>> # }
        """
        state = await orch.materialize_state(session_id=sid)
        return state.model_dump()

    @app.get("/v2/sessions/{sid}/timeline")
    async def get_timeline(sid: str) -> Dict[str, Any]:  # noqa: ANN401
        """Fetch complete event timeline for a session.
        
        Returns all events in the session's append-only event log.
        Useful for audit, replay, and debugging.
        
        Args:
            sid: Session ID from create_session.
        
        Returns:
            JSON object with 'session_id' and 'events' array of SessionEvent objects.
        
        Raises:
            404: If session not found.
        
        Example:
            >>> # GET /v2/sessions/abc123/timeline
            >>> # Response:
            >>> # {
            >>> #   "session_id": "abc123",
            >>> #   "events": [
            >>> #     {"type": "io.input", "data": {...}, ...},
            >>> #     {"type": "decision.started", "data": {...}, ...},
            >>> #     ...
            >>> #   ]
            >>> # }
        """
        events = await orch.list_events(session_id=sid)
        return {"session_id": sid, "events": [e.model_dump() for e in events]}

    @app.get("/v2/metrics")
    async def get_metrics() -> Dict[str, Any]:  # noqa: ANN401
        """Fetch aggregated metrics snapshot.
        
        Returns current counters and latency histograms across all sessions
        (e.g., token count, decision latency, tool execution counts).
        
        Useful for monitoring, dashboards, and performance analysis.
        
        Returns:
            JSON object with 'counters' and 'latencies' sections.
        
        Example:
            >>> # GET /v2/metrics
            >>> # Response:
            >>> # {
            >>> #   "counters": {"token_count": 1500, "decisions": 23, ...},
            >>> #   "latencies": {"decision_ms": [45, 67, 89, ...], ...}
            >>> # }
        """
        return metrics_snapshot()

    async def _sse_gen(
        sid: str, last_event_id: Optional[str] = None
    ) -> AsyncIterator[str]:
        """Generate Server-Sent Events for a session.
        
        Yields historical events first (optionally after last_event_id),
        then streams new events as they occur. Supports SSE resume protocol
        for client reconnection.
        
        Args:
            sid: Session ID to stream events from.
            last_event_id: Optional event ID to resume from (SSE Last-Event-ID).
                If provided, only events after this ID are yielded.
        
        Yields:
            SSE-formatted strings (id: ... \n data: ... \n\n).
        
        Example:
            >>> # GET /v2/sessions/abc123/events with Last-Event-ID: 42
            >>> # Will stream events 43+
        """
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
        """Stream session events via Server-Sent Events (SSE).
        
        Provides a persistent HTTP connection for real-time event streaming.
        Supports the standard SSE Last-Event-ID header for resuming interrupted
        connections.
        
        Args:
            sid: Session ID to stream events from.
            request: FastAPI Request object (used to extract Last-Event-ID header).
        
        Returns:
            StreamingResponse with SSE media type.
        
        Example:
            >>> # GET /v2/sessions/abc123/events
            >>> # Connection: keep-alive
            >>> # Content-Type: text/event-stream
            >>> # id: 1
            >>> # data: {"type": "io.input", "data": {...}, ...}
            >>> # 
            >>> # id: 2
            >>> # data: {"type": "decision.started", ...}
        """
        # Support SSE resume via Last-Event-ID
        last_id = request.headers.get("last-event-id") or request.headers.get(
            "Last-Event-ID"
        )
        return StreamingResponse(
            _sse_gen(sid, last_event_id=last_id), media_type="text/event-stream"
        )

    @app.websocket("/v2/sessions/{sid}/ws")
    async def ws_endpoint(ws: WebSocket, sid: str) -> None:
        """Duplex WebSocket endpoint for real-time session interaction.
        
        Accepts WebSocket connections and manages bidirectional communication:
        - Server → Client: All session events (token frames, decision frames, etc)
        - Client → Server: Input messages or control commands
        
        Message Format:
            Input/control from client should be JSON with 'type' field:
            - {"type": "input", "payload": {...}} -> sends SessionInput
            - {"type": "control", "payload": {...}} -> sends ControlCommand
        
        Args:
            ws: WebSocket connection from client.
            sid: Session ID to attach to.
        
        Example:
            >>> # ws://localhost:8000/v2/sessions/abc123/ws
            >>> # Client sends: {"type": "input", "payload": {"messages": [...]}}
            >>> # Server sends: {"type": "io.token", "data": {...}}
            >>> # Server sends: {"type": "decision.completed", "data": {...}}
        """
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
