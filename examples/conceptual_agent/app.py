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

    # Initial input
    inputs = {
        "messages": [
            {"role": "user", "content": [{"type": "text", "data": "Plan a trip to Tokyo"}]}
        ]
    }

    session = await orch.create_session()
    # Core handles event routing/observability; user code simply consumes stream
    async for _ in orch.stream(session_id=session.id, inputs=inputs):
        # Demonstrate barge-in: cancel mid-stream (conceptual)
        await orch.control(session_id=session.id, command={"type": "cancel.requested"})


if __name__ == "__main__":
    asyncio.run(main())
