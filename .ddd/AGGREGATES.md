# Aggregates, Entities, Value Objects, Invariants

Aggregates (Core)
- Session (Aggregate Root)
  - Entities: StepCursor, Budget, InterruptState
  - Value Objects: SessionId, NodeId, EdgeId, ToolName, Decision
  - Invariants:
    - Single writer (one orchestrator) per Session.
    - State changes only via events appended to the Session’s log.
    - At most one current node at a time.
    - Budgets/timeouts enforced per node/tool call.
    - Interrupts applied at defined boundaries (token/tool chunk/checkpoint).

Aggregates (Graph)
- AgentSpec
  - Entities: Node, Edge
  - Value Objects: NodeId, EdgeId, Condition
  - Invariants:
    - Tools are not nodes; tools are attached to nodes.
    - Edges reference existing NodeIds; conditions validated.
    - Cycles allowed.

Aggregates (Tools)
- ToolRegistry
  - Entities: ToolDef, Permission, Quota
  - Value Objects: ToolName, Timeout, Budget
  - Invariants: Tool signatures and permissions must be validated at compile/use time.

Aggregates (Observe/Security)
- PolicySet (optional later): rate limits, ACLs.
