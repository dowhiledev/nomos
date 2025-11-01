"""Conceptual tools for Nomos vNext example (user code).

Demonstrates progress events, timeouts, budgets, and cancellation-aware execution.
Uses the library-provided `tool` decorator (no placeholder impls here).
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Dict

from pydantic import BaseModel, Field

from nomos.tools import tool  # provided by vNext


class WebSearchArgs(BaseModel):
    query: str = Field(description="User query to search the web")
    top_k: int = Field(5, ge=1, le=20, description="Number of results to return")


@tool(name="web.search", timeout_s=10, budget_tokens=2000)
async def web_search(args: WebSearchArgs, ctx: Dict) -> AsyncIterator[Dict]:
    """Search the web and yield progress.

    Yields:
      {"type": "tool.progress", "stage": "query" | "fetch" | "rank"}
      {"type": "tool.stdout", "line": str}
      Final: {"type": "tool.completed", "results": [...]}
    """
    # observe cancellation
    if ctx.get("cancelled"):
        return

    yield {"type": "tool.progress", "stage": "query", "query": args.query}
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
            {"title": f"Result {i+1} for {args.query}", "url": f"https://example.com/{i+1}"}
            for i in range(args.top_k)
        ],
    }


class SqlQueryArgs(BaseModel):
    dsn: str
    sql: str


@tool(name="db.query", timeout_s=15)
async def db_query(args: SqlQueryArgs, ctx: Dict) -> AsyncIterator[Dict]:
    """Run a SQL query; stream progress and rows."""
    yield {"type": "tool.progress", "stage": "connect", "dsn": args.dsn}
    await asyncio.sleep(0.05)
    yield {"type": "tool.progress", "stage": "execute", "sql": args.sql[:80]}
    await asyncio.sleep(0.05)
    # fake rows
    for i in range(3):
        if ctx.get("cancelled"):
            yield {"type": "tool.error", "error": "cancelled"}
            return
        yield {"type": "tool.stdout", "line": f"row {i}"}
        await asyncio.sleep(0.05)
    yield {"type": "tool.completed", "row_count": 3}


__all__ = ["web_search", "db_query", "WebSearchArgs", "SqlQueryArgs"]
