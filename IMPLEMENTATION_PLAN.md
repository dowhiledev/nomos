Nomos vNext — Implementation Plan

Overview
- Greenfield, developer-first runtime to build event-driven, streaming, multimodal agents.
- No migration constraints. Optimize for clarity, composability, and production-grade primitives.

Core Principles
- Nodes-only graph: nodes are LLM decision steps; tools are invoked inside nodes (ReACT-style).
- Edges encode routing with conditions; cycles supported. Subgraphs compile to Agents; agent-as-tool allowed.
- Event-sourced core with async streaming, interrupts, cancellation, and deterministic replay/checkpoints.
- Library-first usage; server (SSE/WS/gRPC) is optional transport. Core owns event routing/observability.

Prioritized Spikes (No timelines; each yields concrete deliverables)

Spike 1 — Event Schema + Orchestrator Skeleton
- Goals: Canonical event envelope; minimal orchestrator loop with create_session/stream/control/state.
- Scope: Pydantic models for SessionEvent/State; in-memory append-only log; simple state projection.
- Deliverables:
  - `SessionEvent`, `State`, `Session` models
  - Orchestrator: `create_session()`, `stream(session_id, inputs)`, `control(session_id, command)`, `materialize_state()`
  - In-memory event store + projection module
  - Minimal dev harness (CLI entry) for local streaming

Spike 2 — Async LLM Streaming Adapters (OpenAI, Groq)
- Goals: Unified async streaming interface for token/decision output.
- Scope: `stream_decision(messages, schema)` + `stream_generate(messages)`; function/tool-calling parity; error handling.
- Deliverables:
  - Provider shims (openai, groq) with typed outputs
  - Conformance tests (token stream, finish reasons, errors)

Spike 3 — Tool Runner 2.0 (Async, Progress, Cancellation)
- Goals: Async tool contract with progress/partial outputs; budgets/timeouts; safe execution.
- Scope: `@tool` decorator; async generator tools; cancellation tokens; subprocess/threadpool isolation hooks.
- Deliverables:
  - `nomos-tools` runner; progress events (`tool.started|progress|stdout|completed|error`)
  - Budget/timeout enforcement; structured errors; unit tests

Spike 4 — Graph Runtime MVP (Nodes Only)
- Goals: Compose nodes and edges; compile() → Agent; execute via orchestrator.
- Scope: `Graph`, `LLMNode`, `Edge` API; node-level overrides (LLM/tools/memory); cycles allowed.
- Deliverables:
  - Graph builder with validation (no dangling nodes; legal conditions)
  - Compile to Agent (serializable definition)
  - Example parity with `examples/conceptual_agent/graph.py`

Spike 5 — Checkpointing + Replay
- Goals: Deterministic recovery; event-log → state reconstruction; node-boundary checkpoints.
- Scope: Pluggable stores (memory, Redis, Postgres); checkpoint creation/restore APIs.
- Deliverables:
  - Checkpointer plugin interface + Redis/Postgres implementations (JSONB)
  - Replay utility for timeline → state

Spike 6 — SSE/WS Server + TS SDK v2
- Goals: Optional transport to consume events and control sessions remotely.
- Scope: HTTP: create/input/control/state; SSE events; WS bi-directional sessions (send inputs + receive events);
  TS SDK client with types and duplex helpers.
- Deliverables:
  - `nomos-server` with `/v2` endpoints
  - `nomos-sdk-ts` streaming client; examples

Spike 7 — Interrupt Controller + Prioritization
- Goals: Barge-in, pause/resume/cancel; backpressure policies.
- Scope: Priority queues; cooperative cancellation across LLM/tools; control commands; policies.
- Deliverables:
  - Controller module; tests simulating interrupts mid-stream and mid-tool

Spike 8 — Multimodal I/O (Core Contracts)
- Goals: Content-part model; image/audio support in messages/events.
- Scope: Content parts (text/image/audio) normalization; payload chunking; optional media adapters (STT/TTS) later.
- Deliverables:
  - Content model + adapters in providers; tests with simple image prompts

Spike 9 — Subgraphs + Agent-as-Tool
- Goals: Specialization via nested agents; robust adapter to call an Agent like a tool.
- Scope: as_tool adapter; subgraph lifecycle; resource quotas.
- Deliverables:
  - Agent-as-tool wrapper + tests; subgraph example aligned with conceptual sample

Spike 10 — Observability (Tracing, Metrics, Timeline)
- Goals: OTEL spans at node/event granularity; metrics; timeline explorer hooks.
- Scope: Span/link strategy; exporters; sampling; correlation IDs.
- Deliverables:
  - `nomos-observe` setup helpers; default spans around LLM/tool/orchestrator; metrics counters/histograms

Spike 11 — Performance + Scaling
- Goals: Concurrency tuning; worker pools; backpressure and rate limits.
- Scope: LLM/tool worker executors; session sharding; token drop strategies for lagging clients.
- Deliverables:
  - Benchmarks; config knobs; documentation

Spike 12 — Security + Governance
- Goals: Transport auth (JWT/OIDC); rate limiting; tool permissioning; secrets policy.
- Scope: Server middleware; per-tool ACLs; redaction pipelines for event storage.
- Deliverables:
  - Security middleware; tool registry permissions; redaction utilities

Spike 13 — Developer Experience (CLI, Docs, Examples)
- Goals: `nomos dev` hot-reload; templates; improved examples and docs.
- Scope: Reload graph/nodes; local SSE/WS; docs site updates.
- Deliverables:
  - Dev CLI; refreshed examples; quickstarts

Spike 14 — Config / No‑Code Builder (Later)
- Goals: Optional config compiler generating code from YAML/JSON; UI builder on the same contracts.
- Scope: Schema; codegen; import/export of graphs.
- Deliverables:
  - Config compiler; sample UI (“Nomos Compose”) hooks

Acceptance Checks (per spike)
- Unit/integration tests for new surfaces; examples updated to use the new APIs.
- Deterministic replay where applicable; cancellation verified; no blocking calls on hot paths.
- Docs updated (BRAINSTORM.md and this plan) when architecture shifts.

Assumptions & Risks
- Provider streaming/function-calling inconsistencies → normalize via shims + exhaustive tests.
- Cancellation correctness → central tokens and explicit boundaries in LLM/tool runners.
- Event log growth → segment + TTL + compaction via checkpoints/summaries.
- API stability → greenfield now; converge to SemVer once core stabilizes.
