Engineering Guide — Nomos vNext

Purpose
- Set clear, developer-first rules for building the vNext runtime. No migration constraints. High bar for correctness, observability, and UX.

Non‑Negotiables
- No migration constraints: prioritize the best design. Adapters can come later if needed.
- Nodes‑only graphs: nodes are LLM decision steps; tools are invoked inside nodes (ReACT‑style). Tools are not nodes.
- Edges encode routing with conditions; cycles allowed. Subgraphs compile to Agents; agent‑as‑tool supported.
- Core owns event routing/observability: users may consume streams but never reimplement routing.
- Event‑sourced runtime: append‑only events, materialized state, node‑level checkpoints, deterministic replay.
- Async + streaming everywhere: tokens, tool progress, step transitions. Interruptible with pause/resume/cancel.
- Developer‑first: library usage first; server is an optional transport.

Module Boundaries (target layout)
- `nomos.core`: event model, orchestrator, checkpointer, state projection, interrupt controller.
- `nomos.graph`: graph builder (nodes/edges), compile→Agent, subgraph composition; HITL is node behavior, not a node type.
- `nomos.llms-*`: providers with streaming + tool/function‑calling.
- `nomos.tools`: async tool runner, budgets/timeouts/cancellation, isolation options; agent‑as‑tool adapter.
- `nomos.server`: SSE/WS (and optional gRPC) endpoints + auth/limits; thin over core.
- `nomos.observe`: OTEL tracing, metrics, timeline helpers.
- `examples/`: user‑facing code only; no placeholders.

Design Tenets
- Determinism: checkpoint at node boundaries; enable replay to the exact state.
- Cancellation: every long‑running operation must observe cancellation tokens.
- Isolation: support subprocess/threadpool execution for tools; sandbox hooks where needed.
- Performance: avoid blocking calls; prefer async I/O; bound concurrency; apply backpressure.
- Security: no secrets in code; support redaction pipelines for stored events.

Code Style
- Python 3.10+; type hints mandatory for public APIs. Pydantic v2 for schemas.
- Lint/format: ruff (check+format). Type check: mypy/pyright where applicable.
- Logging: structured JSON logs; use core logging helpers. No print statements in libraries.
- Errors: raise typed exceptions with actionable messages; include enough context for debugging (no secrets).

Testing
- Unit tests for graph/orchestrator/providers/tools with async coverage.
- Snapshot tests for decisions/routing; timeline replay tests for determinism.
- Provider shims tested with mocked HTTP; do not depend on external services in CI.
- Include cancellation and interrupt tests (mid‑token, mid‑tool).

Observability
- OTEL spans at node/tool/orchestrator boundaries; propagate session/node ids; link spans to events.
- Metrics for latency, tokens/sec, tool durations, error rates, interrupt handling.
- Timeline explorer hooks: event payloads must be serializable and minimally consistent.

Security & Secrets
- Read secrets from environment or configured vault; never commit keys.
- Redact sensitive fields in events/logs; provide allowlists for safe payloads.
- Respect per‑tool permissions/ACLs; default‑deny policies for unknown tools.

Contribution Rules
- Keep changes minimal and focused; do not introduce placeholders in user examples.
- If you change a core contract (events, orchestrator, graph), update docs: BRAINSTORM.md and IMPLEMENTATION_PLAN.md.
- Add or update tests alongside code; do not weaken coverage for critical paths.
- Breaking changes are acceptable during vNext development; document them clearly in PRs.

Dependencies & Tooling
- Use `uv` to add/remove dependencies (and to manage lockfiles), not raw pip/poetry.
- Manage dev and optional dependencies via pyproject groups/extras (e.g., `uv add package --optional something` or `uv add package --dev`) — keep runtime deps minimal.
- When adding/removing deps, document rationale in PR and ensure CI passes with the intended extras only.

Documentation Discipline
- After completing an overall step or phase, update IMPLEMENTATION_PLAN.md with status and any scope adjustments.
- Keep BRAINSTORM.md and relevant .ddd artifacts in sync when domain/architecture decisions evolve.

Things To Always Remember
- Tools are invoked by nodes; do not add Tool nodes.
- HITL is a node behavior (request input), not a node type.
- The server is optional; library‑first usage is primary.
- Event routing/observability belongs to core; user code should not replicate it.
- No migration constraints: optimize for clarity and correctness.
- Edges carry natural-language conditions for the model/user prompt; runtime does not parse conditions — it validates `Decision.MOVE.step_id` against allowed targets from the current node.
