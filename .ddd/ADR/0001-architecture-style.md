# ADR-0001: Architecture Style

Context
- Nomos vNext requires a real‑time, event‑driven agent runtime with streaming, interrupts, and deterministic replay.
- We target strong domain boundaries, testability, and pluggability of providers/tools/transports.

Decision
- Adopt Domain‑Driven Design + Hexagonal Architecture + Event Sourcing + CQRS.
- Treat each Session as an actor (single orchestrator), processing commands and emitting events.
- Nodes‑only graph; tools invoked within nodes; edges encode routing with cycles; HITL is a node behavior.

Consequences
- Clear ubiquitous language and bounded contexts.
- Ports & Adapters isolate infrastructure (providers/tools/server/observability).
- Event log becomes source of truth; projections serve queries.
- Higher initial ceremony, but improved evolvability and auditability.

Status
- Accepted.

Related
- BRAINSTORM.md, IMPLEMENTATION_PLAN.md, .ddd/*
