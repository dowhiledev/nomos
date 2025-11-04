"""Tool runner implementation executing registered functions with validation and isolation.

SimpleToolRunner is the primary implementation of the ToolRunner protocol.
It provides:
- Function registration via decorator or ToolSpec registry
- Parameter schema validation via Pydantic
- Multiple execution modes (inline, thread, process)
- Timeout and cancellation support
- Event streaming for execution progress
- Tool introspection via get_tools() returning ToolSpec objects
"""

from __future__ import annotations

import asyncio
import inspect
from typing import Any, AsyncIterator, Callable, Dict, List, Optional
from concurrent.futures import ProcessPoolExecutor

from pydantic import BaseModel, create_model

from nomos.core.interfaces import ToolRunner
from nomos.core.tool_events import validate_tool_frame
from nomos.core.types import ToolFrameUnion, ToolArgs
from .spec import ToolSpec


ToolCallable = Callable[..., Any]
"""Type alias for tool functions."""


class ToolExecutionContext:
    """Context object passed to tool functions during execution.

    Allows tools to emit events (progress, output) during execution.
    Tools can call emit() to report progress without waiting for completion.

    Attributes:
        tool_name: Name of the executing tool.

    Example:
        >>> async def my_tool(ctx: ToolExecutionContext) -> str:
        ...     ctx.emit("tool.progress", "Starting...")
        ...     await asyncio.sleep(1)
        ...     ctx.emit("tool.stdout", "Done!")
        ...     return "result"
    """

    def __init__(self, tool_name: str):
        """Initialize execution context.

        Args:
            tool_name: Name of the tool being executed.
        """
        self.tool_name = tool_name
        self._events: List[Dict[str, Any]] = []

    def emit(self, event_type: str, data: Any = None, **kwargs) -> None:
        """Emit a tool event during execution.

        Args:
            event_type: Event type ("tool.progress", "tool.stdout", etc).
            data: Event-specific data. Meaning depends on event_type:
                - For "tool.progress": stage description (string)
                - For "tool.stdout": output line (string)
                - Otherwise: arbitrary data dict
            **kwargs: Additional event fields.

        Example:
            >>> ctx.emit("tool.progress", "phase1")
            >>> ctx.emit("tool.stdout", "Step completed")
        """
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
        """Get all events emitted during execution.

        Returns:
            List of event dicts accumulated via emit() calls.
        """
        return self._events


def _create_tool_schema(func: Callable[..., Any], name: str) -> type[BaseModel]:
    """Create a Pydantic model from function signature.

    Introspects the function to extract parameters and create a schema model
    for validation. Skips special parameters like 'ctx'.

    Args:
        func: Tool function to introspect.
        name: Name for the generated schema class.

    Returns:
        Pydantic BaseModel subclass for parameter validation.
    """
    sig = inspect.signature(func)
    fields = {}

    for param_name, param in sig.parameters.items():
        if param_name == "ctx":
            continue  # Skip context parameter
        if param.default is inspect.Parameter.empty:
            # Required parameter
            fields[param_name] = (param.annotation, ...)
        else:
            # Optional parameter
            fields[param_name] = (param.annotation, param.default)

    return create_model(f"{name}Args", **fields)


def _call_sync(fn: ToolCallable, kwargs: Dict[str, Any]) -> Any:  # noqa: ANN401
    """Call a sync function with kwargs (for process pool executor)."""
    return fn(**kwargs)


class SimpleToolRunner(ToolRunner):
    """Simple implementation of ToolRunner protocol.

    Manages a registry of tool functions and executes them with:
    - Pydantic schema validation
    - ACL/permission checking
    - Configurable execution modes (inline, thread, process)
    - Timeout enforcement
    - Event streaming

    Supports both sync and async functions. Can be used as a context manager
    or decorator for tool registration.

    Example:
        >>> runner = SimpleToolRunner(timeout_s=10.0)
        >>> @runner.tool("add")
        ... def add(a: int, b: int) -> int:
        ...     return a + b
        >>> async for frame in runner.run("add", {"a": 1, "b": 2}, ctx):
        ...     print(frame)
    """

    def __init__(
        self,
        registry: Dict[str, ToolCallable] | None = None,
        *,
        timeout_s: float | None = None,
        execution_mode: str = "inline",  # inline | thread | process
        processes: int | None = None,
    ) -> None:
        """Initialize the tool runner.

        Args:
            registry: Optional dict of {tool_name: ToolSpec}.
            timeout_s: Default timeout in seconds for all tools.
            execution_mode: How to execute functions:
                - "inline": Run synchronously in event loop
                - "thread": Run in thread pool
                - "process": Run in process pool
            processes: Number of processes for "process" mode (default: auto).
        """
        self._registry: Dict[str, ToolSpec] = {}
        self._timeout = timeout_s
        self._exec_mode = execution_mode
        self._proc_pool: ProcessPoolExecutor | None = None
        if self._exec_mode == "process":
            self._proc_pool = ProcessPoolExecutor(max_workers=processes)

        if registry:
            for name, tool_spec in registry.items():
                if not isinstance(tool_spec, ToolSpec):
                    raise TypeError(f"Registry must contain ToolSpec objects, got {type(tool_spec)}")
                self._registry[name] = tool_spec

    def tool(
        self, name: str | None = None, *, description: str | None = None, timeout: float | None = None
    ) -> Callable[[ToolCallable], ToolCallable]:
        """Decorator to register a tool function.

        Args:
            name: Tool name (defaults to function name).
            description: Optional tool description. If not provided, uses the first
                paragraph of the function's docstring.
            timeout: Per-tool timeout in seconds (overrides runner default).

        Returns:
            Decorator that registers the function and returns it unchanged.

        Example:
            >>> @runner.tool("greet", timeout=5.0)
            ... async def greet(name: str) -> str:
            ...     \"\"\"Greet someone.\"\"\"
            ...     return f"Hello, {name}!"
        """

        def decorator(func: ToolCallable) -> ToolCallable:
            tool_name = name or func.__name__
            schema = _create_tool_schema(func, tool_name)
            
            # Use provided description, or extract first paragraph from docstring
            if description is not None:
                tool_description = description
            else:
                doc = func.__doc__ or ""
                # Extract first paragraph (text before first double newline or end of string)
                first_paragraph = doc.split("\n\n")[0].strip()
                tool_description = first_paragraph

            self._registry[tool_name] = ToolSpec(
                name=tool_name,
                func=func,
                schema=schema,
                timeout=timeout,
                description=tool_description,
            )

            return func

        return decorator

    def get_tools(self) -> Dict[str, ToolSpec]:
        """Get all registered tools with full metadata.

        Returns a dict mapping tool names to ToolSpec objects, enabling
        providers and other components to access tool information including
        name, description, schema, timeout, and permissions.

        This method is exposed via the ToolRunner protocol and is used by
        LLM providers to build context-aware prompts with tool schemas
        and descriptions.

        Returns:
            Dict mapping tool names (str) to ToolSpec objects.

        Example:
            >>> runner = SimpleToolRunner()
            >>> @runner.tool("greet")
            ... def greet(name: str) -> str:
            ...     \"\"\"Greet someone.\"\"\"
            ...     return f"Hello, {name}!"
            >>> tools = runner.get_tools()
            >>> tools["greet"].description
            "Greet someone."
            >>> tools["greet"].get_args_json_schema()
            {"type": "object", "properties": {"name": {...}}, ...}
        """
        return self._registry.copy()

    async def run(
        self, tool_name: str, args: ToolArgs, ctx: Dict[str, Any]
    ) -> AsyncIterator[ToolFrameUnion]:
        """Execute a tool and stream execution frames.

        Implements the ToolRunner protocol. Executes the named tool with given
        arguments and streams execution frames (started, progress, completed, error).

        Args:
            tool_name: Name of the tool to execute.
            args: Tool arguments (validated against schema).
            ctx: Execution context (with session_id, node_id, etc).

        Yields:
            ToolFrameUnion frames (ToolStarted, ToolProgress, ToolStdout, ToolCompleted, or ToolError).

        Example:
            >>> async for frame in runner.run("add", {"a": 1, "b": 2}, ctx):
            ...     if frame["type"] == "tool.completed":
            ...         print(f"Result: {frame['result']}")
        """
        tool_spec = self._registry.get(tool_name)
        if not tool_spec:
            yield {"type": "tool.error", "tool": tool_name, "error": "unknown tool"}
            return

        # Validate args against schema
        try:
            validated_args = tool_spec.schema(**args)
            call_kwargs = validated_args.model_dump()
        except Exception as e:
            yield {
                "type": "tool.error",
                "tool": tool_name,
                "error": f"invalid args: {e}",
            }
            return

        # Emit started
        yield {"type": "tool.started", "tool": tool_name}

        fn = tool_spec.func

        # Execute and emit events
        try:
            # Create execution context
            exec_ctx = ToolExecutionContext(tool_name)

            result = await self._execute_tool(tool_spec, call_kwargs, exec_ctx)

            # Yield any events collected during execution
            for event in exec_ctx.get_events():
                yield event

            # Emit completed
            yield {"type": "tool.completed", "tool": tool_name, "result": result}

        except Exception as e:
            yield {"type": "tool.error", "tool": tool_name, "error": str(e)}

    async def _execute_tool(
        self,
        tool_spec: ToolSpec,
        call_kwargs: Dict[str, Any],
        exec_ctx: ToolExecutionContext,
    ) -> Any:
        """Execute the tool function with appropriate timeout and execution mode.

        Internal method that handles:
        - Async vs sync function detection
        - Execution mode selection (inline, thread, process)
        - Timeout enforcement
        - Context injection

        Args:
            tool_spec: ToolSpec with tool metadata and function.
            call_kwargs: Validated arguments for the tool.
            exec_ctx: Execution context to pass to tool.

        Returns:
            The tool's return value.

        Raises:
            Exception: Any exception from tool execution.
            asyncio.TimeoutError: If timeout is exceeded.
        """
        fn = tool_spec.func

        # Add execution context if function accepts it
        sig = inspect.signature(fn)
        if "ctx" in sig.parameters:
            call_kwargs["ctx"] = exec_ctx

        # Determine timeout
        timeout = tool_spec.timeout or self._timeout

        # Execute based on function type and execution mode
        # Check if async by looking at __wrapped__ if decorated
        is_async = inspect.iscoroutinefunction(getattr(fn, "__wrapped__", fn))

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
                    loop.run_in_executor(None, lambda: fn(**call_kwargs)),
                    timeout=timeout,
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
                    timeout=timeout,
                )
            else:
                result = await loop.run_in_executor(
                    self._proc_pool, _call_sync, fn, call_kwargs
                )
        else:
            # Inline sync
            if timeout:
                result = await asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(
                        None, lambda: fn(**call_kwargs)
                    ),
                    timeout=timeout,
                )
            else:
                result = fn(**call_kwargs)

        return result


async def _iterate_with_timeout(
    agen: AsyncIterator[Dict[str, Any]], timeout: float
) -> AsyncIterator[Dict[str, Any]]:
    """Iterate an async generator with a timeout applied to awaiting the next item.

    Args:
        agen: Async generator to iterate.
        timeout: Timeout in seconds for each iteration step.

    Yields:
        Items from the async generator.

    Raises:
        asyncio.TimeoutError: If timeout is exceeded waiting for next item.
    """
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
