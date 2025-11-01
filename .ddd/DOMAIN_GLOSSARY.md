# Domain Glossary (Ubiquitous Language)

- Agent: A compiled, runnable graph that makes decisions and can call tools.
- Graph: A definition composed of Nodes and Edges; compiles to an Agent.
- Node (Step): A decision point driven by an LLM that may call tools (ReACT‑style) and emit a Decision.
- Edge (Route): A conditional transition from one Node to another based on a Decision.
- Tool: An async capability invoked by a Node (not a Node itself). Emits progress/stdout/completed/error events.
- Agent‑as‑Tool: Treating an Agent as a Tool for specialization or delegation.
- Decision: Structured output from a Node indicating action (RESPOND/MOVE/TOOL_CALL/END) and related data.
- Session: A running conversational context for one Agent; owns event log, policies, and budgets.
- Event (SessionEvent): Canonical, append‑only record of something that happened in a Session.
- State (Projection): Materialized view derived from events for queries/UI.
- Checkpoint: Durable snapshot at node boundaries for fast resume and deterministic replay.
- Orchestrator: Session controller that processes commands, drives nodes/tools, and emits events.
- Interrupt: Control input (pause/resume/cancel/checkpoint) that changes runtime behavior.
- Provider: External LLM service implementing the provider port (OpenAI, Groq, etc.).
- Tool Runner: Executor for tools providing progress and cancellation semantics.
- Transport: Server endpoints (HTTP/SSE/WS/gRPC) to interact with Sessions remotely.
- Observability: Tracing/metrics/logging providing timeline and performance insights.
- HITL: Human‑in‑the‑loop behavior inside a Node (requesting user input) — not a standalone Node type.
