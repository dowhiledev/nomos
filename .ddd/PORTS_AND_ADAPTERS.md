# Ports & Adapters (Hexagonal)

Domain Ports (interfaces defined by Core)
- LLMProviderPort
  - stream_decision(messages, schema) → async iterator of tokens + final parsed decision
  - stream_generate(messages) → async iterator of tokens + final text
- ToolRunnerPort
  - run(tool_name, args, ctx) → async iterator of tool.progress/stdout/completed/error
- EventStorePort
  - append(session_id, events[]) ; read_by_session(session_id) ; subscribe(session_id)
- CheckpointStorePort
  - save(session_id, checkpoint) ; load(session_id, checkpoint_id)
- TransportPort (optional)
  - create_session, input, stream, control, get_state
- MetricsPort / TracingPort
  - counters, histograms, span lifecycle helpers

Adapters (infrastructure)
- Providers: OpenAI/Groq/… implement LLMProviderPort
- Tools: Python tools, MCP, API wrappers implement ToolRunnerPort
- Stores: Redis/Postgres/S3/Kafka implement EventStore/CheckpointStore
- Server: FastAPI/WS/gRPC implement TransportPort
- Observe: OTEL exporter, Prometheus implement telemetry ports

Anti‑Corruption Layers
- Providers normalize function/tool‑calling deltas and finish reasons to domain Decision/Token events.
- Tools normalized to progress/stdout/completed/error frames with typed payloads.
