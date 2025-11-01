# Security & Governance

Auth & Transport
- Server transport supports JWT/OIDC; rate limits per tenant/session.
- CLI/library auth via tokens/env; secrets never stored in code.

Tool Permissions
- Default‑deny with allowlists per agent/node. Per‑tool budgets, timeouts, and scopes.
- Agent‑as‑Tool inherits caller’s policy with optional overrides.

Event/Log Redaction
- Redact PII/secrets fields in events/logs. Provide allowlists for safe keys.

Multi‑Tenant Isolation
- Namespacing for sessions; quotas for concurrent sessions/tools.

Supply‑Chain
- Hash/pin provider SDK versions; verify MCP tool specs; sandbox risky tools where feasible.
