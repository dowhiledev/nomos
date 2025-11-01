# Nomos vNext — Domain-Driven Design Pack

This folder captures the DDD process and artifacts for Nomos vNext. It documents the domain language, bounded contexts, aggregates, commands/events, ports, and non‑functional concerns. No code lives here; it’s a living guide for consistent design and implementation.

Contents
- DOMAIN_GLOSSARY.md — Ubiquitous language
- BOUNDED_CONTEXTS.md — Context map and relationships
- AGGREGATES.md — Aggregates, entities, value objects, invariants
- COMMANDS.md — Command catalog (write side)
- DOMAIN_EVENTS.md — Event catalog (event sourcing)
- USE_CASES.md — Event‑storming flows and scenarios
- CQRS_READ_MODELS.md — Projections and queries (read side)
- PORTS_AND_ADAPTERS.md — Hexagonal ports and adapter responsibilities
- OBSERVABILITY.md — Tracing/metrics/logging and event <-> telemetry mapping
- SECURITY_AND_GOVERNANCE.md — Auth, rate limits, ACL, redaction
- ADR/0001-architecture-style.md — Architecture decision record

How to use
1) Start with DOMAIN_GLOSSARY and BOUNDED_CONTEXTS.
2) For a new capability, add/adjust commands, events, invariants, and ports.
3) Keep events canonical. If infrastructure changes, add an adapter; do not change domain events casually.
4) Update ADRs for fundamental choices.
