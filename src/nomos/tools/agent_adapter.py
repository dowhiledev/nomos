from __future__ import annotations

from typing import Any, AsyncIterator, Callable, Dict, Optional

from nomos.core import Orchestrator
from nomos.core.events import EventType
from nomos.core.ports import LLMProviderPort, ToolRunnerPort
from nomos.graph import AgentSpec


ToolCallable = Callable[..., Any]


def as_tool(
    agent: Optional[AgentSpec],
    *,
    provider: LLMProviderPort,
    tool_runner: Optional[ToolRunnerPort] = None,
) -> ToolCallable:
    """Adapt an Agent (or None) to a tool callable.

    The returned callable signature is compatible with SimpleToolRunner.
    It expects `messages` (list) in kwargs, and an optional `ctx` containing `cancel_event`.
    """

    async def _tool_fn(
        *, messages: list[dict], ctx: Optional[Dict[str, Any]] = None, **_: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        ctx = ctx or {}
        cancel_event = ctx.get("cancel_event")
        orch = Orchestrator(agent=agent, provider=provider, tool_runner=tool_runner)
        session = await orch.create_session()
        # Start streaming the sub-agent
        async for ev in orch.stream(
            session_id=session.id, inputs={"messages": messages}
        ):
            if (
                cancel_event is not None
                and getattr(cancel_event, "is_set", lambda: False)()
            ):
                yield {"type": "tool.error", "error": "cancelled"}
                return
            et = ev.get("type")
            if et == EventType.TOKEN_EMITTED.value:
                yield {"type": "tool.stdout", "line": ev.get("data", {}).get("delta")}
            elif et.startswith("tool."):
                # forward nested tool frames as progress for visibility
                yield {"type": "tool.progress", "stage": et, "frame": ev}
            elif et == EventType.DECISION_COMPLETED.value:
                yield {"type": "tool.completed", "result": ev.get("data")}
                return

    return _tool_fn


__all__ = ["as_tool"]
