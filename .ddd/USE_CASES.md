# Event‑Storming Flows & Use Cases

UC1 — Simple Q&A with Streaming
- Trigger: SubmitInput(user asks a question)
- Flow:
  1) DecisionStarted → TokenEmitted* → DecisionCompleted(RESPOND)
  2) (optional) CheckpointCreated
- Non‑functional: token latency, accurate finish reasons

UC2 — Tool Use in a Node (ReACT)
- Trigger: SubmitInput(query requiring external info)
- Flow:
  1) DecisionStarted → DecisionCompleted(TOOL_CALL)
  2) ToolStarted → ToolProgress* → ToolCompleted → DecisionStarted
  3) TokenEmitted* → DecisionCompleted(RESPOND/MOVE)
- Invariants: tool budgets/timeouts; cancellation safe points

UC3 — Routing with Cycles (Refinement)
- Flow:
  1) DecisionCompleted(MOVE:iterate) → RoutingApplied(into same node)
  2) Repeat until DecisionCompleted(MOVE:next)

UC4 — Interrupt/Barge‑in Mid‑Token
- Trigger: ApplyControl(cancel) while TokenEmitted is ongoing
- Flow: CancelApplied(scope=decision) → Decision stops → CheckpointCreated

UC6 — Bidirectional Session (Duplex)
- Flow:
  1) Receiver consumes stream; Sender enqueues SubmitInput concurrently
  2) Orchestrator interleaves events with new inputs; ensures consistency

Notes
- Asterisks (*) denote repeated events.
