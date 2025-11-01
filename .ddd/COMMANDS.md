# Command Catalog (Write Side)

Session Commands
- CreateSession { agent_id, options }
- SubmitInput { session_id, messages[] }  # user input (multimodal)
- ApplyControl { session_id, type: pause|resume|cancel|checkpoint }
- Advance { session_id }  # optional tick if idle

Node/Decision Commands (issued internally by orchestrator)
- StartDecision { session_id, node_id }
- RouteNext { session_id, from_node_id, condition }

Tool Commands (issued internally)
- InvokeTool { session_id, node_id, tool_name, args }
- CancelTool { session_id, tool_call_id }

Checkpoint Commands
- CreateCheckpoint { session_id, node_id }
- RestoreCheckpoint { session_id, checkpoint_id }

Notes
- Commands are intent; they do not change state directly. Handlers validate invariants and emit events.
