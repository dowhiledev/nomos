"""Conceptual library-first runner for Nomos vNext example (user code).

Streams events from the orchestrator and demonstrates interrupts/barge-in.
No placeholder classes here; imports assume vNext APIs exist.
"""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Dict, List

from nomos.core import Orchestrator  # provided by vNext
from nomos.core.events import EventType
from nomos.tools.runner import SimpleToolRunner
from examples.conceptual_agent.tools import web_search


class DemoProvider:
    async def stream_decision(self, messages: List[Dict[str, Any]], schema: Any) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Emit a token and then ask to call the web.search tool
        yield {"type": EventType.TOKEN_EMITTED.value, "data": {"role": "assistant", "delta": "Working... "}}
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {
                "action": "TOOL_CALL",
                "tool_call": {"tool_name": "web.search", "tool_kwargs": {"query": "Tokyo budget itinerary", "top_k": 3}},
            },
        }
        # After tool completes, provider would normally be called again. For demo, finish here.


async def main() -> None:
    # No graph routing needed for MVP demo; focus on streaming + tool call
    orch = Orchestrator(agent=None, provider=DemoProvider(), tool_runner=SimpleToolRunner({"web.search": web_search}))

    # Multimodal input: text + image
    inputs = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "data": "Plan a 3-day Tokyo trip under $1500"},
                    {"type": "image", "data": {"url": "https://example.com/tokyo.jpg"}, "mime": "image/jpeg"},
                ],
            }
        ]
    }

    session = await orch.create_session()
    # Core handles routing/observability; user prints tokens, tool frames, and decision
    async for evt in orch.stream(session_id=session.id, inputs=inputs):
        if evt["type"] == EventType.TOKEN_EMITTED.value:
            print(evt["data"].get("delta"), end="", flush=True)
        elif evt["type"].startswith("tool."):
            print("\n", evt)
            if evt["type"] == "tool.completed":
                break
        elif evt["type"] == EventType.DECISION_COMPLETED.value:
            print("\n[done]", evt["data"]) 
            break


if __name__ == "__main__":
    asyncio.run(main())
