Nomos vNext — Event-Driven, Streaming, Multimodal Agent Runtime

Summary
- Greenfield, developer-first redesign: no migration constraints; prioritize code-first APIs and runtime primitives. Config/no‑code generation comes later.
- Re-architect Nomos from a synchronous step runner into an event-sourced, async, streaming runtime with first-class multimodality, multi-agent orchestration, and deep observability.
- Core pillars: Async by default, Event-driven execution, Token/step streaming, Interruptibility, Tool concurrency + cancellation, Multimodal I/O, Pluggable state and checkpointing, Production-grade observability.
- Competitive aim: match and surpass LangGraph’s state graph + checkpointing model and Google ADK’s real-time, multimodal, event loop by offering a unified, developer-friendly architecture with stronger tool/runtime primitives and auditable event logs.

Developer-First Positioning
- Code-first: Python APIs to define graphs, nodes, and tools; event routing/observability handled by core; server is optional.
- Explicit over implicit: minimal magic, strong typing, predictable execution semantics.
- Power-user ergonomics: hot-reload dev server, structured logs, rich tracing, and deterministic replay.
- Config and low-code: added later via generators on top of stable core APIs (YAML/JSON optional, not required).

What’s Broken/Constrained in .old (and why it matters)
- Synchronous execution path
  - Session/Agent `next` is sync and blocks on LLM and tools.
  - Async tools are forced through `asyncio.run`, causing event-loop conflicts and latency spikes.
  - Consequence: No partial responses, no concurrent tool work, poor latency, hard to cancel/interrupt.

- No token or step streaming
  - LLM providers use non-streaming methods, and API offers only request/response endpoints.
  - Consequence: Poor UX for long responses; no real-time UI updates; hard to debug stuck steps.

- Limited eventing and observability
  - Events exist but are emitted from a few hot spots and only as side-effects. No consistent event schema or end-to-end event log.
  - Tracing is patched in, not native; spans miss granular lifecycle events (token, tool progress, routing decisions).
  - Consequence: Hard to replay, audit, and correlate issues; debugging across distributed components is painful.

- Tool model is sync-first and non-cancellable
  - Tool.run validates then executes (sync). Async tools are wrapped through `asyncio.run`.
  - No progress or partial outputs; no cancellation protocol; no isolation (resource/time limits) or budgets.
  - Consequence: A single slow tool blocks the agent; can’t support barge-in or graceful abort; unsafe for prod.

- Session and memory are not event-sourced
  - State is directly mutated and only snapshots are persisted; pickling is used in places.
  - Consequence: No deterministic replay; difficult to implement robust checkpointing, recovery, or time-travel debugging.

- Multimodality is bolted-on (text-centric)
  - Message model is text-first. No first-class content parts (image/audio) or unified multimodal I/O contracts.
  - Consequence: Hard to support vision/audio models and real-time voice UX.

- Interrupts/barge-in are unsupported
  - No facility to accept user or system interrupts while a step/tool is running or while tokens are streaming.
  - Consequence: Cannot build conversational/voice experiences that feel real-time and controllable.

- Multi-agent orchestration is minimal
  - No graph-based execution or robust supervisor/worker patterns, nor parallel subgraphs.
  - Consequence: Complex workflows become brittle; little support for specialization and team-of-agents patterns.

- Scaling model is limited
  - Stateless API exists, but the runtime is tightly coupled and synchronous; only coarse horizontal scaling.
  - Consequence: Weak throughput under load; no backpressure; difficult to shard or distribute steps.


Design Goals for vNext
- Async-first and streaming everywhere (LLM tokens, tool progress, step transitions).
- Event-sourced runtime with a typed event schema and immutable append-only log.
- Deterministic replay and checkpointing (per-session and per-node).
- Multimodal I/O primitives (text, image, audio) with consistent content-part contracts.
- Tooling 2.0: async, cancellable, resource-bounded, progress/partial outputs, MCP-native.
- Multi-agent orchestration via a typed graph (DAG) runtime with parallelism, subgraphs, and roles.
- First-class interrupts and barge-in (stop, pause, resume, reroute) with prioritization.
- Deep observability: traces, metrics, logs, and full event timeline; easy to audit and visualize.
- Pluggable persistence and transport (Redis/Postgres/Kafka, WebSocket/SSE/gRPC, vector stores).
- DX: ergonomic builders, type-safe schema generation, strong testing/mocking utilities.

Package/Module Layout (proposed)
- `nomos-core`: event model, orchestrator, checkpointer, state projection.
- `nomos-graph`: graph runtime, node contract (Step/LLM), edges/conditions, subgraph composition; HITL as node behavior.
- `nomos-llms-*`: provider shims (openai, groq, anthropic, google, ollama) with streaming + function calling.
- `nomos-tools`: tool runner, isolation/sandbox, MCP client integration; agent-as-tool adapter.
- `nomos-server`: HTTP/SSE + WebSocket endpoints; optional gRPC; auth hooks; rate-limits.
- `nomos-observe`: OTEL setup, metrics exporters, timeline explorer helpers.
- `nomos-sdk-ts`: TS client for event streams + control plane (types from OpenAPI + event schemas).


Proposed Architecture
1) Runtime Layers
- Transport Layer
  - Ingress: HTTP+SSE for simple clients; WebSocket (bi-directional tokens/events); optional gRPC.
  - Egress: Event streams (SSE/WS) per session; system telemetry via OTLP.

- Orchestrator (Session Controller)
  - Owns a session’s event loop. Consumes Commands (user input, interrupts) and drives the Execution Graph.
  - Publishes canonical SessionEvents (token, tool.start|progress|end, decision, transition, error, checkpoint, etc.).
  - Enforces budgets, timeouts, backpressure; handles cancellation and preemption.

- Execution Graph (NomosGraph)
  - Typed DAG with event-sourcing; nodes are decision steps (LLM-driven) that can call tools internally (ReACT-style).
  - Tools are not nodes. Edges carry natural-language conditions for prompting (documentation), not executable rules.
  - The node’s Decision chooses a next step via `MOVE` + `step_id`; runtime validates the target against allowed edges.
  - Subgraphs compile to Agents and can be referenced as tools (agent-as-tool) for specialization.
  - Graph execution is async; node work can run concurrently where applicable; each node emits NodeEvents.
  - Checkpointer plugin persists node-level checkpoints and composes session-level checkpoint metadata.

- State & Checkpointing
  - Event Log is source of truth. State is a projection built from events (replayable, versioned schema).
  - Pluggable stores: Postgres (JSONB), S3 (log segments), Redis (hot state), Kafka (stream fan-out).
  - Durable checkpoints at node boundaries to enable resume/replay after failures.

- Capability Adapters
  - LLMs: async streaming providers with unified token/event interface, including tool/function-calling and image/audio support.
  - Tools: wrappers for Python callables, MCP servers, REST/RPC APIs; async execution with cancellation and progress updates; agent-as-tool.
  - Memory: vector store adapters (pgvector, Weaviate, qdrant), BM25, hybrid (as components, not nodes).
  - Media: STT/TTS adapters (Whisper, Deepgram, Realtime APIs), image pre/post-processing.

Library-First API (primary usage)
- Compose and run graphs in-process; server transport is optional.
- Example sketch (nodes-only; tools called inside nodes; edges encode routing):
  - agent = (
      Graph(name="demo", llm="openai:gpt-4o")
        .add(
          LLMNode(id="intake", prompt="collect requirements"),
          LLMNode(id="work", prompt="do work with tools", tools=[web_search, db_query, as_tool(specialist)]),
          LLMNode(id="finalize", prompt="produce final output")
        )
        .edge(Edge("intake", "work", when="MOVE:work"))
        .edge(Edge("work", "finalize", when="MOVE:finalize"))
        .compile()
    )
  - session = await Orchestrator(agent).create_session()
  - async for evt in Orchestrator(agent).stream(session_id=session.id, inputs=...):
      ... # optional consumption; core handles routing/observability

2) Event Model (first-class contract)
- Core envelope: SessionEvent { session_id, event_id, ts, type, data, span_ctx }
- Event types (non-exhaustive):
  - io.token (delta, role, content_part)
  - decision.started | decision.completed
  - tool.started | tool.progress | tool.stdout | tool.completed | tool.error
  - route.candidate | route.selected
  - step.enter | step.exit | flow.enter | flow.exit
  - interrupt.requested | interrupt.applied | cancel.requested | cancel.applied
  - checkpoint.created | checkpoint.restored
  - error (llm|tool|runtime|validation)
- Contracts include minimal standard fields + an extensible data payload. Designed for storage and SSE/WS fan-out.

3) Async + Streaming LLM Interface
- Unified async provider interface:
  - stream_decision(messages, response_schema) -> async iterator of TokenEvents + final ParsedDecision
  - stream_generate(messages) -> async iterator of TokenEvents + final text
- Function/tool-calling: stream_fn_calls emits partial args, tool-choice, and function delta events.
- Multimodal: content parts (text, image, audio bytes/url) normalized; providers translate to native payloads.

4) Tooling 2.0
- ToolDefinition: schema, permissions, budgets, timeouts, isolation (subprocess/threadpool, optional sandbox).
- Execution API:
  - run(args, ctx) -> async iterator emitting tool.progress/tool.stdout events; supports cancellation tokens via ctx["cancel_event"].
  - Return structured results; optionally stream partial result frames.
  - Developer ergonomics: `@tool` decorator + `registry_from_tools` to register and configure tools (name, timeout, permissions). Basic ACL supported in runner.
- MCP-native: server registry, discovery, health check; tools pulled at runtime; streaming over MCP where possible.
- Concurrency: multiple tool calls in parallel; scheduler enforces session/tenant budgets.

5) Interrupts & Barge-in
- Interaction Controller merges inbound commands (user input, cancel, pause, resume) into session priority queues.
- Cooperative cancellation: LLM streams and tool runners observe cancellation tokens; Orchestrator sets a session-level cancel_event that tools receive via ctx.
- Policies: immediate abort, graceful stop-at-boundary, or preempt + resume via checkpoint.
- Voice UX: barge-in interrupts TTS mid-playback; system resumes listening and adapts next state.

6) Multimodal I/O
- Message model adopts content parts: [{type: "text"|"image"|"audio"|... , data, mime, metadata}].
- STT/TTS integrated into the graph as nodes; audio streams in/out via WS or WebRTC gateway (optional module).
- Image handling includes vision prompts and tool outputs (e.g., annotations) as content parts.

7) Multi-Agent Orchestration
- Topologies: Supervisor-Worker, Debate, Specialist Panels, DAG pipelines, hierarchical planners.
- Shared channel bus per team: agents communicate via typed events with routing keys and ACLs.
- Subgraph spawning: ephemeral sub-agents for specialized tasks; resource quotas; lifecycle events.
 - Agent-as-tool adapter: construct a tool from an Agent and provider; nested agent tokens stream as tool.stdout; returns tool.completed with decision.
- Coordination nodes: RouterNode with learned or rule-based policies; Vote/Merge nodes with reducers.

8) Observability & Telemetry
- OpenTelemetry baked-in at node/event granularity. Every token/tool progress is trace-linked.
- Metrics: per-session latency, tokens/sec, error rates, tool durations, interrupt reactions. Lightweight defaults provided (counters + timing histograms), OTEL optional.
- Logs: structured JSON; optional sampling; correlation IDs for session, node, tool.
- Timeline explorer API: query events by session/node/time; replay timeline in UI.
 - Metrics endpoint `/v2/metrics` exposes counters and timing averages for quick introspection (OTEL optional).

9) API Surface (Server)
- HTTP:
  - POST /v2/sessions -> create (returns stream URL + snapshot)
  - POST /v2/sessions/{id}/input -> enqueue user input/command (non-blocking)
 - GET  /v2/sessions/{id}/events -> SSE stream of SessionEvents
    - Emits per-event `id` fields for resume; honors `Last-Event-ID` header to replay missed events before live tail.
  - GET  /v2/sessions/{id}/state -> current materialized state
  - POST /v2/sessions/{id}/control -> {cancel, pause, resume, checkpoint}
- WebSocket:
  - Bi-directional sessions: send user inputs and receive events over one connection; supports backpressure and acks.
- gRPC (optional): streaming APIs mirroring WS for typed, high-throughput backends.
Note: The server is an optional transport layer; the core dev workflow is library-first. Event routing/observability are handled by the core; users may simply consume streams or use the server’s SSE/WS endpoints.

10) Persistence & Scaling
- Stateless orchestrators; durable event log + checkpoint store provide recovery and scale-out.
- Worker pools for LLM and tool nodes; distribute by session hash or step shard key.
- Backpressure strategies: drop tokens to UI if lagging; prioritize control/interrupt events; throttle tool concurrency.
- Cloud-native: K8s-friendly; Kafka for fan-out, Redis for hot cache, Postgres/S3 for durable logs.


Developer Experience
- Graph Builder DSL
  - Python-first builder for nodes/edges with type hints; YAML/JSON import/export for low-code users.
  - Compile-time validation: node contracts, missing schemas, cycles, and permission checks.

- Strong Schemas
  - Pydantic v2 models for decisions and tool args; schema evolution with versioning.
  - Codegen for TS SDK types from OpenAPI + event schemas.

- Testing Harness
  - Deterministic replays from event logs; snapshot tests for node outputs and routing decisions.
  - LLM mocks with canned token streams; tool runners with fake progress and cancellation.

- Dev Workflow
  - `nomos dev` hot-reloads nodes/graphs and exposes a local SSE/WS stream for rapid iteration.
  - Rich debug panels (tokens, events, tool stdout) and timeline scrubbing.
  - First-class fixtures for unit and integration tests; hermetic tool runner with fake time and budgets.

No Migration Constraints
- Treat vNext as a greenfield runtime. Focus on the best design without backwards compatibility.
- Provide optional adapters later if needed, but do not limit the core with legacy concerns.


Roadmap (Phased)
Phase 1 — Core Runtime & Streaming (weeks 1–4)
- Implement Session Orchestrator, Event schema, SSE endpoint, async OpenAI/Groq providers with token streams.
- Tool runner with async/cancel/timeouts; minimal progress events; execution budgets.
- Replace pickle with JSON State + minimal checkpointing; OTEL spans around nodes.

Phase 2 — Graph + Checkpointing (weeks 3–6)
- NomosGraph runtime with decision nodes (LLM) only; tools invoked inside nodes; edges/conditions control routing; cycles supported; HITL as node behavior.
- Checkpointer plugin (Redis + Postgres) and basic replay; deterministic routing where possible.
- TS SDK v2 with event stream consumption; basic CLI to inspect timelines.

Phase 3 — Multimodal + Interrupts (weeks 5–8)
- Content-part message model; image and audio adapters; streaming audio in/out over WS.
- Interrupt controller with barge-in; cooperative cancellation across LLM/tools; control API.

Phase 4 — Multi-Agent + Observability UX (weeks 7–10)
- Team graphs (supervisor/worker, debate); subgraph spawn/join; quotas.
- Timeline explorer and tracing dashboards; richer metrics.


How We Intentionally Differ From Competitors
- Versus LangGraph:
  - Event-sourced core with full token/tool progress in the canonical log (stronger replay/audit).
  - Multimodal and tool streaming as first-class citizens, not bolt-ons.
  - Built-in interrupt controller and cancellation across LLM and tool layers.

- Versus Google ADK:
  - Bring ADK-like real-time, multimodal loop to any model/provider and on-prem.
  - Unify graph orchestration with event sourcing and checkpointing for long-running flows.
  - Strong Python DX with cross-language event contracts and TS SDK parity.


Key APIs (Sketches)
- LLM Provider
  - async def stream_decision(messages, schema) -> AsyncIterator[TokenEvent]; returns ParsedDecision at end
  - async def stream_generate(messages) -> AsyncIterator[TokenEvent]; returns final text

- Tool Runner
  - async def run(args, ctx: ToolContext) -> AsyncIterator[ToolEvent]; supports cancel via ctx.cancelled

- Orchestrator
  - create_session() -> Session
  - stream(session_id, inputs=None) -> AsyncIterator[SessionEvent]
  - input(session_id, inputs) -> ack (enqueue user messages)
  - control(session_id, command) -> ack (pause/resume/cancel/checkpoint)
  - materialize_state(session_id) -> State


Initial Data Model (Event Sourcing)
- SessionEvent
  - id, ts, session_id, type, node_id, payload (JSON), span_ctx
  - Stored append-only; State is computed projection: {current_node, memory, last_tokens, last_tool_result, checkpoints}


Risks & Mitigations
- Provider inconsistencies for streaming/function-calling → normalize with shims, add exhaustive tests.
- Cancellation correctness across threads/processes → central cancellation tokens and explicit boundaries.
- Event log growth → segment + TTL + compaction via checkpoints and summaries.
- Multimodal payload sizes → chunking, CDN/S3 offload, signed URLs for large media.
- API stability → clear versioning and deprecation policy once core stabilizes; prioritize semantic versioning.


Quick Wins While Building vNext
- Replace synchronous `Tool.run` with async wrapper + cancellation and timeouts.
- Add SSE endpoint for step/decision/token events without changing client requests.
- Convert session persistence to JSON + eliminate pickle usage.
- Introduce minimal Event schema and emit from all critical points (LLM start/end, tool start/end, transitions).


Deliverables Checklist
- Event schema + stores (in-memory, Redis, Postgres)
- Async LLM streaming for 1–2 providers (OpenAI, Groq)
- Async ToolRunner with cancel/timeouts and progress; agent-as-tool adapter
- SSE/WS server endpoints + TS SDK v2
- NomosGraph MVP (decision nodes only; edges routing; subgraphs) + Checkpointing
- Interrupt controller + control APIs
- Multimodal content-part model + image/voice adapters (MVP)

Config/No‑Code (Later Phase)
- Stabilize core APIs first. Then:
- Add config loader that compiles YAML/JSON graphs into code; generate stubs for nodes/tools.
- Optional UI builder (“Nomos Compose”) on top of the same event schemas and graph contracts.
