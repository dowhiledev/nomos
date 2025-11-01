# Bounded Contexts & Context Map

Contexts
- Core (nomos-core)
  - Orchestrator (session actor), Session, Events, State projection, Checkpointing, Interrupts.
- Graph (nomos-graph)
  - Graph builder (Nodes/Edges), compile→Agent, validation, subgraph composition.
- Tools (nomos-tools)
  - Tool definitions & runner, budgets/timeouts/cancellation, agent-as-tool adapter.
- LLM Providers (nomos-llms-*)
  - Provider shims (OpenAI/Groq/…), streaming decisions, function/tool-calling.
- Server (nomos-server)
  - HTTP/SSE/WS transports; auth, rate limits; no domain logic.
- Observe (nomos-observe)
  - OTEL, metrics, timeline integrations.

Context Relationships
- Upstream → Downstream
  - Graph → Core: Core consumes compiled Agents from Graph.
  - Tools → Core: Core invokes tools via ToolRunnerPort.
  - Providers → Core: Core invokes LLM via LLMProviderPort.
  - Core → Server: Server exposes Core’s application services (transport port).
  - Core → Observe: Observability consumes Core events/spans (sidecar / exporter).

Integration Styles
- Graph → Core: Published Language (Agent spec), Anti‑corruption Layer (compile checks).
- Tools/Providers → Core: Ports & Adapters boundary; Core defines interfaces; adapters conform.
- Server → Core: Ports & Adapters; Server is an adapter to TransportPort.

Context Map (Textual)
- Core is the domain kernel.
- Graph is an upstream model supplier (Published Language).
- Tools/Providers are downstream infrastructure, isolated by ports (Conformist to domain interfaces).
- Server is a downstream transport (Conformist to domain interfaces).
- Observe is a supporting subsystem (separate concerns, no domain coupling).
