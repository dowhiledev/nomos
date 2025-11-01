# CQRS Read Models (Projections)

Projections (examples)
- SessionState
  - session_id, current_node, last_action, suggestions, history_tail, flow_state, checkpoints
- Timeline
  - ordered events with cursors; filter by type/time/node/tool
- ToolRuns
  - per tool_call_id: start/end, duration, stages, errors
- Metrics Snapshot
  - tokens/sec, decision latency, tool durations, error rates

Query API (examples)
- get_state(session_id)
- get_timeline(session_id, from_event_id?, types?)
- list_sessions(limit, offset)
- get_tool_runs(session_id, tool_name?)

Notes
- Projections are eventually consistent; rebuild from event log when schemas evolve.
