"""Conceptual bidirectional (duplex) session demo.

Shows a real-time, back-and-forth conversation where both the user and agent can
send/receive concurrently. The core handles routing/observability; user code
manages sending inputs and consuming the event stream.
"""

from __future__ import annotations

import asyncio
from typing import Dict, List

from nomos.core import Orchestrator  # provided by vNext
from .graph import make_agent


async def sender(orch: Orchestrator, session_id: str, lines: List[str]) -> None:
    for line in lines:
        # Simulate user typing/messages over time
        await asyncio.sleep(0.1)
        payload: Dict = {
            "messages": [{"role": "user", "content": [{"type": "text", "data": line}]}]
        }
        await orch.input(session_id=session_id, inputs=payload)


async def receiver(orch: Orchestrator, session_id: str) -> None:
    async for evt in orch.stream(session_id=session_id):
        if evt["type"] == "io.token":
            print(evt["data"].get("delta"), end="", flush=True)
        elif evt["type"].startswith("tool."):
            print("\n", evt)
        elif evt["type"] == "decision.completed":
            print("\n[turn complete]", evt["data"])


async def main() -> None:
    agent = make_agent()
    orch = Orchestrator(agent)
    session = await orch.create_session()

    # Kick off receiver (event stream) and sender (user inputs) concurrently
    user_lines = [
        "Hello!",
        "Plan a 3-day Tokyo trip under $1500",
        "Prefer sushi spots and anime shopping",
        "Thanks!",
    ]

    await asyncio.gather(
        receiver(orch, session.id),
        sender(orch, session.id, user_lines),
    )


if __name__ == "__main__":
    asyncio.run(main())
