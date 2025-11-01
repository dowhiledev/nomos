"""Simple tool runner implementing ToolRunnerPort over a registry of callables.

Tools can be registered via the @runner.tool() decorator, which generates schemas
and handles event emission automatically.
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass
from typing import Any, AsyncIterator, Awaitable, Callable, Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor

from pydantic import BaseModel, create_model

from nomos.core.ports import ToolRunnerPort
from nomos.core.tool_events import validate_tool_frame
from nomos.core.types import ToolFrameType, ToolArgs


ToolCallable = Callable[..., Any]


@dataclass
class ToolInfo:
    """Metadata for a registered tool."""
    func: ToolCallable
    schema: type[BaseModel]
    timeout: Optional[float]
    description: str


class ToolExecutionContext:
    """Context passed to tool functions for emitting events."""
    
    def __init__(self, tool_name: str):
        self.tool_name = tool_name
        self._events: List[Dict[str, Any]] = []
    
    def emit(self, event_type: str, data: Any = None, **kwargs) -> None:
        """Emit a tool event."""
        event = {"type": event_type, "tool": self.tool_name}
        if data is not None:
            if isinstance(data, dict):
                event.update(data)
            else:
                # For tool.progress, data is the stage
                # For tool.stdout, data is the line
                if event_type == "tool.progress":
                    event["stage"] = str(data)
                elif event_type == "tool.stdout":
                    event["line"] = str(data)
                else:
                    event["data"] = data
        event.update(kwargs)
        self._events.append(event)
    
    def get_events(self) -> List[Dict[str, Any]]:
        """Get collected events."""
        return self._events


def _create_tool_schema(func: Callable[..., Any], name: str) -> type[BaseModel]:
    """Create a Pydantic model from function signature."""
    sig = inspect.signature(func)
    fields = {}
    
    for param_name, param in sig.parameters.items():
        if param_name == 'ctx':
            continue  # Skip context parameter
        if param.default is inspect.Parameter.empty:
            # Required parameter
            fields[param_name] = (param.annotation, ...)
        else:
            # Optional parameter
            fields[param_name] = (param.annotation, param.default)
    
    return create_model(f"{name}Args", **fields)


def _call_sync(fn: ToolCallable, kwargs: Dict[str, Any]) -> Any:  # noqa: ANN401
    return fn(**kwargs)


class SimpleToolRunner(ToolRunnerPort):
    def __init__(
        self,
        registry: Dict[str, ToolCallable] | None = None,
        *,
        timeout_s: float | None = None,
        allowed_tools: set[str] | None = None,
        execution_mode: str = "inline",  # inline | thread | process
        processes: int | None = None,
    ) -> None:
        self._registry: Dict[str, ToolInfo] = {}
        self._timeout = timeout_s
        self._allowed = allowed_tools
        self._exec_mode = execution_mode
        self._proc_pool: ProcessPoolExecutor | None = None
        if self._exec_mode == "process":
            self._proc_pool = ProcessPoolExecutor(max_workers=processes)
        
        # Backward compatibility: if registry provided, populate from old format
        if registry:
            for name, func in registry.items():
                schema = _create_tool_schema(func, name)
                description = func.__doc__ or ""
                timeout = getattr(func, "__tool_timeout__", None)
                self._registry[name] = ToolInfo(
                    func=func,
                    schema=schema,
                    timeout=timeout,
                    description=description.strip()
                )

    def tool(
        self, 
        name: str | None = None, 
        *, 
        timeout: float | None = None
    ) -> Callable[[ToolCallable], ToolCallable]:
        """Decorator to register a tool function.
        
        Args:
            name: Tool name. If None, uses function name.
            timeout: Tool timeout in seconds.
        """
        def decorator(func: ToolCallable) -> ToolCallable:
            tool_name = name or func.__name__
            schema = _create_tool_schema(func, tool_name)
            description = func.__doc__ or ""
            
            self._registry[tool_name] = ToolInfo(
                func=func,
                schema=schema,
                timeout=timeout,
                description=description.strip()
            )
            
            # Set metadata for backward compatibility
            setattr(func, "__tool_name__", tool_name)
            setattr(func, "__tool_timeout__", timeout)
            
            return func
        
        return decorator

    async def run(
        self, tool_name: str, args: ToolArgs, ctx: Dict[str, Any]
    ) -> AsyncIterator[ToolFrameType]:
        # ACL check
        if self._allowed is not None and tool_name not in self._allowed:
            yield {"type": "tool.error", "tool": tool_name, "error": "unauthorized"}
            return
        
        tool_info = self._registry.get(tool_name)
        if not tool_info:
            yield {"type": "tool.error", "tool": tool_name, "error": "unknown tool"}
            return

        # Validate args against schema
        try:
            validated_args = tool_info.schema(**args)
            call_kwargs = validated_args.model_dump()
        except Exception as e:
            yield {"type": "tool.error", "tool": tool_name, "error": f"invalid args: {e}"}
            return

        # Emit started
        yield {"type": "tool.started", "tool": tool_name}

        fn = tool_info.func
        
        # Backward compatibility: if async generator, use old behavior
        if inspect.isasyncgenfunction(fn):
            async def _execute_old_style():
                # Add ctx if function accepts it
                sig = inspect.signature(fn)
                if "ctx" in sig.parameters:
                    call_kwargs["ctx"] = ctx
                
                res = fn(**call_kwargs)
                async for frame in res:
                    try:
                        fr = validate_tool_frame(frame)
                        yield fr.model_dump()
                    except Exception:
                        yield {
                            "type": "tool.error",
                            "tool": tool_name,
                            "error": "invalid frame",
                        }
            
            # adopt per-tool timeout
            timeout = tool_info.timeout or self._timeout
            if timeout:
                agen = _execute_old_style()
                try:
                    async for frame in _iterate_with_timeout(agen, timeout):
                        yield frame
                except asyncio.TimeoutError:
                    yield {"type": "tool.error", "tool": tool_name, "error": "timeout"}
            else:
                async for frame in _execute_old_style():
                    yield frame
            return

        # New style: execute and emit events
        try:
            # Create execution context
            exec_ctx = ToolExecutionContext(tool_name)
            
            result = await self._execute_tool(tool_info, call_kwargs, exec_ctx)
            
            # Yield any events collected during execution
            for event in exec_ctx.get_events():
                yield event
            
            # Emit completed
            yield {"type": "tool.completed", "tool": tool_name, "result": result}
                
        except Exception as e:
            yield {"type": "tool.error", "tool": tool_name, "error": str(e)}

    async def _execute_tool(
        self, tool_info: ToolInfo, call_kwargs: Dict[str, Any], exec_ctx: ToolExecutionContext
    ) -> Any:
        """Execute the tool function with appropriate timeout and execution mode."""
        fn = tool_info.func
        
        # Add execution context if function accepts it
        sig = inspect.signature(fn)
        if "ctx" in sig.parameters:
            call_kwargs["ctx"] = exec_ctx
        
        # Determine timeout
        timeout = tool_info.timeout or self._timeout
        
        # Execute based on function type and execution mode
        # Check if async by looking at __wrapped__ if decorated
        is_async = inspect.iscoroutinefunction(getattr(fn, '__wrapped__', fn))
        
        if is_async:
            # Async function
            coro = fn(**call_kwargs)
            if timeout:
                result = await asyncio.wait_for(coro, timeout=timeout)
            else:
                result = await coro
        elif self._exec_mode == "thread":
            loop = asyncio.get_running_loop()
            if timeout:
                result = await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: fn(**call_kwargs)), timeout=timeout
                )
            else:
                result = await loop.run_in_executor(None, lambda: fn(**call_kwargs))
        elif self._exec_mode == "process":
            loop = asyncio.get_running_loop()
            if self._proc_pool is None:
                self._proc_pool = ProcessPoolExecutor()
            if timeout:
                result = await asyncio.wait_for(
                    loop.run_in_executor(self._proc_pool, _call_sync, fn, call_kwargs), 
                    timeout=timeout
                )
            else:
                result = await loop.run_in_executor(self._proc_pool, _call_sync, fn, call_kwargs)
        else:
            # Inline sync
            if timeout:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, lambda: fn(**call_kwargs)), 
                    timeout=timeout
                )
            else:
                result = fn(**call_kwargs)
        
        return result


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


__all__ = ["SimpleToolRunner", "ToolExecutionContext"]
