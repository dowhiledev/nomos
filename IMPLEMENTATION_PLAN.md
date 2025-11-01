Nomos vNext — Implementation Plan

Overview
- Greenfield, developer-first runtime to build event-driven, streaming, multimodal agents.
- No migration constraints. Optimize for clarity, composability, and production-grade primitives.

Core Principles
- Nodes-only graph: nodes are LLM decision steps; tools are invoked inside nodes (ReACT-style).
- Edges encode routing with conditions; cycles supported. Subgraphs compile to Agents; agent-as-tool allowed.
- Event-sourced core with async streaming, interrupts, cancellation, and deterministic replay/checkpoints.
- Library-first usage; server (SSE/WS/gRPC) is optional transport. Core owns event routing/observability.

Alignment With DDD + Hexagonal + ES/CQRS
- Follow .ddd artifacts as the source of truth for ubiquitous language, contexts, aggregates, commands/events, and ports.
- Treat each Session orchestrator as an actor handling commands and emitting events to an append‑only log.
- Define ports first, backed by contract tests, then deliver adapters over time.

Milestones & Spikes (No timelines; each yields concrete deliverables)

Milestone 0 — DDD Foundations (documentation only)
- Goals: Establish domain language and boundaries; stabilize event names and port surfaces.
- Deliverables:
  - .ddd/DOMAIN_GLOSSARY.md, BOUNDED_CONTEXTS.md, AGGREGATES.md (done)
  - .ddd/COMMANDS.md, DOMAIN_EVENTS.md, USE_CASES.md (done)
  - .ddd/PORTS_AND_ADAPTERS.md, OBSERVABILITY.md, SECURITY_AND_GOVERNANCE.md (done)
  - ADR/0001-architecture-style.md (done)
- Exit Criteria: Stakeholder sign‑off on events, commands, and initial ports.
 - Status: Completed

Spike 1 — Event Schema + Orchestrator Skeleton (actor)
- Goals: Canonical event envelope; minimal orchestrator loop with create_session/stream/control/state.
- Scope: Pydantic models for SessionEvent/State; in-memory append-only log; simple state projection.
- Deliverables:
  - `SessionEvent`, `State`, `Session` models
  - Orchestrator: `create_session()`, `stream(session_id, inputs)`, `control(session_id, command)`, `materialize_state()`
  - In-memory event store + projection module
  - Minimal dev harness (CLI entry) for local streaming
 - Status: Completed (core skeleton + in-memory store + basic projection)

Spike 2 — Port Contracts + Contract Tests
- Goals: Lock the behavior of ports before adapters (providers/tools/stores/transports).
- Scope: Define `LLMProviderPort`, `ToolRunnerPort`, `EventStorePort`, `CheckpointStorePort`, `TransportPort`, Metrics/Tracing.
- Deliverables:
  - Contract tests (fixtures + fake adapters) verifying streaming, cancellation, and error semantics
  - Port docs linked back to .ddd/PORTS_AND_ADAPTERS.md
 - Status: Completed (event store, provider, tool runner, checkpoint store contracts in tests)

Spike 3 — Async LLM Streaming Adapter (OpenAI)
- Goals: Unified async streaming interface for token/decision output (OpenAI only for MVP).
- Scope: `stream_decision(messages, schema)` + `stream_generate(messages)`; error handling; content-parts mapping.
- Deliverables:
  - OpenAIProvider adapter with typed outputs
  - Conformance tests (token stream, completion aggregation, errors)
 - Status: Completed
   - OpenAIProvider supports token streaming, RESPOND aggregation, basic tool/function-calling deltas → TOOL_CALL.
   - Content-parts mapping implemented (text, image-url). Error behavior covered via fake/malformed clients. Real client behind optional extra.

Spike 4 — Tool Runner 2.0 (Async, Progress, Cancellation)
- Goals: Async tool contract with progress/partial outputs; budgets/timeouts; safe execution.
- Scope: `@tool` decorator; async generator tools; cancellation tokens; subprocess/threadpool isolation hooks.
 - Deliverables:
  - `nomos-tools` runner; progress events (`tool.started|progress|stdout|completed|error`)
  - Budget/timeout enforcement; structured errors; unit tests
 - Status: Completed
   - SimpleToolRunner supports async generators and coroutines; passes ctx (including cancel_event) to tools.
   - Per-frame timeout enforced; unknown tools yield structured errors; mid-tool cancel tested via orchestrator cancel.

Spike 5 — Graph Runtime MVP (Nodes Only)
- Goals: Compose nodes and edges; compile() → Agent; execute via orchestrator.
- Scope: `Graph`, `LLMNode`, `Edge` API; node-level overrides (LLM/tools/memory); cycles allowed.
 - Deliverables:
  - Graph builder with validation (no dangling nodes; legal conditions)
  - Compile to Agent (serializable definition)
  - Example parity with `examples/conceptual_agent/graph.py`
 - Status: Completed
   - AgentSpec with MOVE/RESPOND routing; validation (dangling edges, reachability, duplicates).
   - Builder DSL fixed for Pydantic v2 and isolation; prompt helper added; tests for builder isolation.

Spike 6 — Checkpointing + Replay
- Goals: Deterministic recovery; event-log → state reconstruction; node-boundary checkpoints.
- Scope: Pluggable stores (memory, Redis, Postgres); checkpoint creation/restore APIs.
 - Deliverables:
  - Checkpointer plugin interface + Redis/Postgres implementations (JSONB)
  - Replay utility for timeline → state
 - Status: Completed
   - In-memory checkpoint store and APIs for create/restore; events emitted.
   - Replay utility projects timeline → state; parity verified with materialized state.

Spike 7 — WS/SSE Server (duplex)
- Goals: Optional transport to consume events and control sessions remotely.
- Scope: HTTP: create/input/control/state; WS bi-directional sessions (send inputs + receive events). SSE endpoint provided as best-effort (automated test deferred due to client flakiness).
- Deliverables:
  - `nomos-server` with `/v2` endpoints (HTTP + WS; SSE provided)
 - Status: In progress (FastAPI app with WS + SSE endpoints; SSE now emits per-event ids and supports Last-Event-ID resume; WS/timeline tests passing; SSE test remains skipped due to TestClient flakiness)

Spike 8 — Interrupt Controller + Prioritization
- Goals: Barge-in, pause/resume/cancel; backpressure policies.
- Scope: Priority queues; cooperative cancellation across LLM/tools; control commands; policies.
 - Deliverables:
  - Controller module; tests simulating interrupts mid-stream and mid-tool
 - Status: In progress (cancel + pause/resume groundwork; cancel tests added)

Spike 9 — Multimodal I/O (Core Contracts)
- Goals: Content-part model; image/audio support in messages/events.
- Scope: Content parts (text/image/audio) normalization; payload chunking; optional media adapters (STT/TTS) later.
 - Deliverables:
  - Content model + adapters in providers; tests with simple image prompts
 - Status: Pending

Spike 10 — Subgraphs + Agent-as-Tool
- Goals: Specialization via nested agents; robust adapter to call an Agent like a tool.
- Scope: as_tool adapter; subgraph lifecycle; resource quotas.
 - Deliverables:
  - Agent-as-tool wrapper + tests; subgraph example aligned with conceptual sample
 - Status: In progress (agent-as-tool adapter provided in `nomos.tools.agent_adapter.as_tool`; end-to-end test with nested tool invocation added)

Spike 11 — Observability (Tracing, Metrics, Timeline)
- Goals: OTEL spans at node/event granularity; metrics; timeline explorer hooks.
- Scope: Span/link strategy; exporters; sampling; correlation IDs.
 - Deliverables:
  - `nomos-observe` setup helpers; default spans around LLM/tool/orchestrator; metrics counters/histograms
 - Status: In progress (lightweight counters + timing metrics via measure(); spans around provider/tool/orchestrator boundaries; SSE emits event ids for timeline resume; metrics snapshot available at `/v2/metrics`)

Spike 12 — Performance + Scaling
- Goals: Concurrency tuning; worker pools; backpressure and rate limits.
- Scope: LLM/tool worker executors; session sharding; token drop strategies for lagging clients.
 - Deliverables:
  - Benchmarks; config knobs; documentation
 - Status: Pending

Spike 13 — Security + Governance
- Goals: Transport auth (JWT/OIDC); rate limiting; tool permissioning; secrets policy.
- Scope: Server middleware; per-tool ACLs; redaction pipelines for event storage.
 - Deliverables:
  - Security middleware; tool registry permissions; redaction utilities
 - Status: Pending

Spike 14 — Developer Experience (CLI, Docs, Examples)
- Goals: `nomos dev` hot-reload; templates; improved examples and docs.
- Scope: Reload graph/nodes; local SSE/WS; docs site updates.
 - Deliverables:
  - Dev CLI; refreshed examples; quickstarts
 - Status: Pending

Spike 15 — Config / No‑Code Builder (Later)
- Goals: Optional config compiler generating code from YAML/JSON; UI builder on the same contracts.
- Scope: Schema; codegen; import/export of graphs.
 - Deliverables:
  - Config compiler; sample UI (“Nomos Compose”) hooks
 - Status: Pending

Milestone Grouping & Exit Criteria
- M1 Foundations (0,1,2): DDD docs signed off; event schema stable; ports defined and contract‑tested.
  - Exit: At least one fake provider/tool passes contract tests; in‑memory event store usable.
- M2 Runtime MVP (3,4,5): Provider + Tool runner + Graph compile integrated with actor orchestrator.
  - Exit: Conceptual example runs locally with streaming and a simple tool call.
  - Status: Completed
- M3 Transport (6,7): Server endpoints operational (duplex).
  - Exit: curl/web client can create session, stream WS, send inputs and control; e2e demo. SSE endpoint available, automated test optional.
  - Status: In progress
- M4 Multimodal & Interrupts (8,9): Content‑parts and robust interrupt controller.
  - Exit: Image prompt works; mid‑token and mid‑tool cancel tested.
- M5 Specialization & Observability (10,11): Subgraphs + agent‑as‑tool; tracing/metrics.
  - Exit: Specialist sub‑agent example; spans and metrics visible.
- M6 Scale & Security (12,13): Performance + limits + auth/permissions/redaction.
  - Exit: Basic load benchmark meets SLO; auth and tool ACLs enforced.
- M7 DX & Config (14,15): Dev CLI; optional config pipeline.
  - Exit: `nomos dev` hot‑reload usable; config compiler baseline.

Acceptance Checks (per spike)
- Unit/integration tests for new surfaces; examples updated to use the new APIs.
- Deterministic replay where applicable; cancellation verified; no blocking calls on hot paths.
- Docs updated (BRAINSTORM.md and this plan) when architecture shifts.

Assumptions & Risks
- Provider streaming/function-calling inconsistencies → normalize via shims + exhaustive tests.
- Cancellation correctness → central tokens and explicit boundaries in LLM/tool runners.
- Event log growth → segment + TTL + compaction via checkpoints/summaries.
- API stability → greenfield now; converge to SemVer once core stabilizes.
