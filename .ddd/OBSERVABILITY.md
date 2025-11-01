# Observability Strategy

Goals
- Full timeline of a session, token streams, tool progress, routing, and checkpoints.
- Low overhead, high fidelity; link telemetry to events.

Traces (OTEL)
- Spans around: Orchestrator cycle, LLM call (DecisionStarted→Completed), Tool run, Checkpoint save/load.
- Attributes: session_id, node_id, tool_name, call_id, counts, durations.
- Links: TokenEmitted/ToolProgress events link to their parent spans.

Metrics
- Counters: events by type; errors by scope; interrupts applied.
- Histograms: decision latency, tool durations, tokens/sec.
- Gauges: active sessions, in‑flight tools.

Logs
- Structured JSON with correlation ids; redacted sensitive payloads.

Event ↔ Telemetry Mapping
- DecisionStarted → start LLM span
- TokenEmitted → increment tokens/sec; link to LLM span
- ToolStarted/Progress/Completed → tool spans; progress logs; duration histograms
- CheckpointCreated/Restored → checkpoint spans
- ErrorOccurred → error counters; span status
