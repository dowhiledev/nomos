"""Simple tool runner implementing ToolRunnerPort over a registry of callables.

A tool is expected to be an async generator that yields frames (dicts) such as:
  {"type": "tool.started", ...}
  {"type": "tool.progress", ...}
  {"type": "tool.stdout", ...}
  {"type": "tool.completed", ...}
  {"type": "tool.error", ...}

If the callable is an async coroutine (not a generator), it will be executed and
its result will be wrapped in a single `tool.completed` frame.
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, AsyncIterator, Awaitable, Callable, Dict

from nomos.core.ports import ToolRunnerPort


ToolCallable = Callable[..., Any]


class SimpleToolRunner(ToolRunnerPort):
    def __init__(self, registry: Dict[str, ToolCallable], *, timeout_s: float | None = None) -> None:
        self._registry = registry
        self._timeout = timeout_s

    async def run(self, tool_name: str, args: Dict[str, Any], ctx: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        fn = self._registry.get(tool_name)
        if not fn:
            yield {"type": "tool.error", "tool": tool_name, "error": "unknown tool"}
            return

        async def _execute() -> AsyncIterator[Dict[str, Any]]:
            call_kwargs = dict(args)
            # Pass ctx if the tool supports it (parameter name 'ctx' or **kwargs available)
            try:
                sig = inspect.signature(fn)
                params = sig.parameters
                if "ctx" in params or any(p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()):
                    call_kwargs["ctx"] = ctx
            except Exception:
                # best-effort; fall back to not passing ctx
                pass
            res = fn(**call_kwargs)
            if inspect.isasyncgen(res):
                async for frame in res:  # type: ignore[async-for-over-async-iterable]
                    yield frame
                return
            if asyncio.iscoroutine(res) or isinstance(res, Awaitable):
                value = await res  # type: ignore[func-returns-value]
            else:
                value = res
            yield {"type": "tool.completed", "tool": tool_name, "result": value}

        # Emit started
        yield {"type": "tool.started", "tool": tool_name}

        agen = _execute()
        try:
            if self._timeout:
                async for frame in _iterate_with_timeout(agen, self._timeout):
                    yield frame
            else:
                async for frame in agen:
                    yield frame
        except asyncio.TimeoutError:
            yield {"type": "tool.error", "tool": tool_name, "error": "timeout"}


async def _iterate_with_timeout(agen: AsyncIterator[Dict[str, Any]], timeout: float) -> AsyncIterator[Dict[str, Any]]:
    async for item in agen:
        # apply timeout per frame delivery
        yield await asyncio.wait_for(asyncio.sleep(0, result=item), timeout=timeout)


__all__ = ["SimpleToolRunner"]
