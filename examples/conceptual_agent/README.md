# Conceptual Agent (vNext)

Developer-first, code-centric example showing how to use Nomos vNext’s event-driven, streaming runtime. The local app demonstrates streaming and a simple tool call.

Highlights
- Graph-based orchestration (LLM, Router; tools are invoked from nodes; subgraphs supported)
- Streaming tokens and tool progress
- Interrupts and barge-in (pause/resume/cancel)
- Multimodal I/O (text, image, audio) with content parts
- Event-sourced state and checkpointing
- Optional SSE/WS server integration
- Multi-agent team topology with supervisor/worker subgraphs

Key Files
- `graph.py` – defines the graph (nodes/edges) and sub-agents
- `tools.py` – conceptual tools with progress, timeouts, and budgets
- `app.py` – library-first orchestrator usage with streaming + tool call
- `server.py` – optional SSE/WS server endpoints
- `NOTES.md` – design notes guiding the example

Usage (conceptual)
- Library-first: import `make_agent()`, create an `Orchestrator`, and stream events locally.
- Server is optional; enable SSE/WS for remote clients if needed.

Local session (client‑managed)
- Run: `python -m examples.conceptual_agent.app`
- The demo provider streams a token, requests a `web.search` tool call, and the tool streams progress → completed.

Bidirectional session (duplex, client‑managed)
```
import asyncio
from examples.conceptual_agent.bidirectional_app import main

# Starts a receiver that consumes the agent's event stream
# and a sender that enqueues user messages concurrently.
asyncio.run(main())
```

Server‑side session (remote)
1) Run the server
```
uvicorn examples.conceptual_agent.server:app --reload
```

2) Create a session (HTTP)
```
curl -s -X POST http://localhost:8000/v2/sessions | jq
# -> { "session_id": "..." }
```

3) Send input (HTTP)
```
curl -s -X POST \
  http://localhost:8000/v2/sessions/<SESSION_ID>/input \
  -H 'Content-Type: application/json' \
  -d '{
        "messages": [{
          "role": "user",
          "content": [
            {"type": "text", "data": "Plan a 3-day Tokyo trip"},
            {"type": "image", "data": {"url": "https://example.com/tokyo.jpg"}, "mime": "image/jpeg"}
          ]
        }]
      }'
```

4) Stream events (SSE)
```
curl -N http://localhost:8000/v2/sessions/<SESSION_ID>/events
# prints token deltas, tool.progress, decision.completed, etc.
```

5) Interrupt from client (HTTP)
```
curl -s -X POST \
  http://localhost:8000/v2/sessions/<SESSION_ID>/control \
  -H 'Content-Type: application/json' \
  -d '{ "type": "cancel.requested" }'
```

Notes
- Tools are invoked by nodes or the provider’s tool-call decisions; the example uses a SimpleToolRunner mapping `web.search`.
- For client‑managed sessions, you can persist session ids/state on the client and pass them back into `stream`/`control` calls.
- Duplex: For truly bidirectional experiences, use WebSocket endpoints on the server
  (`/v2/sessions/{id}/ws`) or the library’s `input()` + `stream()` concurrently.
