"""Conceptual tools for Nomos vNext example (user code).

Demonstrates progress events, timeouts, budgets, and cancellation-aware execution.
Implements simple async generator tools compatible with SimpleToolRunner.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict


async def web_search(
    query: str, top_k: int = 5, ctx: Dict | None = None
) -> AsyncIterator[Dict]:
    """Search the web and yield progress.

    Yields:
      {"type": "tool.progress", "stage": "query" | "fetch" | "rank"}
      {"type": "tool.stdout", "line": str}
      Final: {"type": "tool.completed", "results": [...]}
    """
    # observe cancellation
    ctx = ctx or {}
    if ctx.get("cancelled"):
        return

    yield {"type": "tool.progress", "stage": "query", "query": query}
    await asyncio.sleep(0.1)
    yield {"type": "tool.stdout", "line": "Fetching from sources..."}
    await asyncio.sleep(0.1)
    yield {"type": "tool.progress", "stage": "fetch"}
    await asyncio.sleep(0.1)
    if ctx.get("cancelled"):
        yield {"type": "tool.error", "error": "cancelled"}
        return
    yield {
        "type": "tool.completed",
        "results": [
            {
                "title": f"Result {i + 1} for {query}",
                "url": f"https://example.com/{i + 1}",
            }
            for i in range(top_k)
        ],
    }


async def db_query(dsn: str, sql: str, ctx: Dict | None = None) -> AsyncIterator[Dict]:
    """Run a SQL query; stream progress and rows."""
    ctx = ctx or {}
    yield {"type": "tool.progress", "stage": "connect", "dsn": dsn}
    await asyncio.sleep(0.05)
    yield {"type": "tool.progress", "stage": "execute", "sql": sql[:80]}
    await asyncio.sleep(0.05)
    # fake rows
    for i in range(3):
        if ctx.get("cancelled"):
            yield {"type": "tool.error", "error": "cancelled"}
            return
        yield {"type": "tool.stdout", "line": f"row {i}"}
        await asyncio.sleep(0.05)
    yield {"type": "tool.completed", "row_count": 3}


__all__ = ["web_search", "db_query"]
