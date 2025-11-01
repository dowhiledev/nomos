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
from concurrent.futures import ProcessPoolExecutor
from nomos.core.ports import ToolRunnerPort
from nomos.core.tool_events import validate_tool_frame
from nomos.core.types import ToolContext, ToolFrameType, ToolArgs


ToolCallable = Callable[..., Any]


def _call_sync(fn: ToolCallable, kwargs: Dict[str, Any]) -> Any:  # noqa: ANN401
    return fn(**kwargs)


class SimpleToolRunner(ToolRunnerPort):
    def __init__(
        self,
        registry: Dict[str, ToolCallable],
        *,
        timeout_s: float | None = None,
        allowed_tools: set[str] | None = None,
        execution_mode: str = "inline",  # inline | thread | process
        processes: int | None = None,
    ) -> None:
        self._registry = registry
        self._timeout = timeout_s
        self._allowed = allowed_tools
        self._exec_mode = execution_mode
        self._proc_pool: ProcessPoolExecutor | None = None
        if self._exec_mode == "process":
            self._proc_pool = ProcessPoolExecutor(max_workers=processes)

    async def run(
        self, tool_name: str, args: ToolArgs, ctx: ToolContext
    ) -> AsyncIterator[ToolFrameType]:
        # ACL check
        if self._allowed is not None and tool_name not in self._allowed:
            yield {"type": "tool.error", "tool": tool_name, "error": "unauthorized"}
            return
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
                if "ctx" in params or any(
                    p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
                ):
                    call_kwargs["ctx"] = ctx
            except Exception:
                # best-effort; fall back to not passing ctx
                pass
            res = fn(**call_kwargs)
            if inspect.isasyncgen(res):
                async for frame in res:  # type: ignore[async-for-over-async-iterable]
                    try:
                        fr = validate_tool_frame(frame)
                        yield fr.model_dump()
                    except Exception:
                        yield {
                            "type": "tool.error",
                            "tool": tool_name,
                            "error": "invalid frame",
                        }
                return
            if asyncio.iscoroutine(res) or isinstance(res, Awaitable):
                value = await res  # type: ignore[func-returns-value]
            else:
                if self._exec_mode == "thread":
                    loop = asyncio.get_running_loop()
                    value = await loop.run_in_executor(None, lambda: res)
                elif self._exec_mode == "process":
                    # Only supports sync functions; if coroutine/generator was returned we wouldn't be here
                    loop = asyncio.get_running_loop()
                    if self._proc_pool is None:
                        self._proc_pool = ProcessPoolExecutor()
                    value = await loop.run_in_executor(
                        self._proc_pool, _call_sync, fn, call_kwargs
                    )
                else:
                    value = res
            yield {"type": "tool.completed", "tool": tool_name, "result": value}

        # Emit started
        yield {"type": "tool.started", "tool": tool_name}

        # adopt per-tool timeout metadata if runner-level timeout not set
        to = self._timeout
        if to is None:
            to = getattr(fn, "__tool_timeout__", None)
        agen = _execute()
        try:
            if to:
                async for frame in _iterate_with_timeout(agen, to):
                    yield frame
            else:
                async for frame in agen:
                    yield frame
        except asyncio.TimeoutError:
            yield {"type": "tool.error", "tool": tool_name, "error": "timeout"}


async def _iterate_with_timeout(
    agen: AsyncIterator[Dict[str, Any]], timeout: float
) -> AsyncIterator[Dict[str, Any]]:
    """Iterate an async generator with a timeout applied to awaiting the next item."""
    try:
        anext = agen.__anext__  # type: ignore[attr-defined]
    except AttributeError:  # pragma: no cover - defensive
        # Fallback: consume via async for but timeout cannot be enforced between yields
        async for item in agen:
            yield item
        return
    while True:
        try:
            item = await asyncio.wait_for(anext(), timeout=timeout)
        except StopAsyncIteration:
            break
        yield item


__all__ = ["SimpleToolRunner"]
