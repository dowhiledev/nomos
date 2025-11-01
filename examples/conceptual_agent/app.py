"""Conceptual library-first runner for Nomos vNext example (user code).

Streams events from the orchestrator and demonstrates interrupts/barge-in.
No placeholder classes here; imports assume vNext APIs exist.
"""

from __future__ import annotations

import asyncio
from typing import Dict

from nomos.core import Orchestrator  # provided by vNext
from .graph import make_agent


async def main() -> None:
    agent = make_agent()
    orch = Orchestrator(agent)

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
    sent_cancel = False
    # Core handles routing/observability; user prints tokens and interrupts when needed
    async for evt in orch.stream(session_id=session.id, inputs=inputs):
        if evt["type"] == "io.token":
            print(evt["data"].get("delta"), end="", flush=True)
            if not sent_cancel:
                await orch.control(session_id=session.id, command={"type": "cancel.requested"})
                sent_cancel = True
        elif evt["type"].startswith("tool."):
            print("\n", evt)
        elif evt["type"] == "decision.completed":
            print("\n[done]", evt["data"]) 


if __name__ == "__main__":
    asyncio.run(main())
