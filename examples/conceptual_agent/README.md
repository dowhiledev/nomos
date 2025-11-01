# Conceptual Agent (vNext)

Developer-first, code-centric example showing how to use Nomos vNext’s event-driven, streaming runtime. This is a design reference and not runnable yet.

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
- `app.py` – library-first orchestrator usage with streaming
- `server.py` – optional SSE/WS server endpoints
- `NOTES.md` – design notes guiding the example

Usage (conceptual)
- Library-first: import `Graph`, compose nodes, create `Orchestrator`, and stream `SessionEvent`.
- Server is optional; enable SSE/WS for remote clients if needed.

Note: Namespaces referenced (e.g., `nomos_graph`, `nomos_core`) represent the proposed vNext packages and serve as placeholders here.
