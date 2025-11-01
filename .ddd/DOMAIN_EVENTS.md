# Domain Event Catalog (Event Sourcing)

Session Lifecycle
- SessionCreated { session_id, agent_id }
- SessionEnded { session_id, reason }

Inputs & Decisions
- InputEnqueued { session_id, messages[] }
- DecisionStarted { session_id, node_id }
- TokenEmitted { session_id, node_id, role, delta }
- DecisionCompleted { session_id, node_id, action, response?, step_id?, tool_call? }
- RoutingApplied { session_id, from_node_id, to_node_id, condition }

Tools
- ToolStarted { session_id, node_id, tool_name, call_id }
- ToolProgress { session_id, node_id, tool_name, call_id, stage }
- ToolStdout { session_id, node_id, tool_name, call_id, line }
- ToolCompleted { session_id, node_id, tool_name, call_id, result }
- ToolError { session_id, node_id, tool_name, call_id, error }

Interrupts & Control
- ControlApplied { session_id, type: pause|resume|cancel|checkpoint }
- CancelApplied { session_id, scope: decision|tool }

Checkpoints
- CheckpointCreated { session_id, node_id, checkpoint_id }
- CheckpointRestored { session_id, node_id, checkpoint_id }

Errors
- ErrorOccurred { session_id, scope: llm|tool|runtime, message }

Notes
- Events are immutable and append‑only; schema versioning applies for evolution.
