"""Decorators and utilities for tool registration and management.

This module provides decorators to mark functions as tools and automatically
build a registry for use by tool runners. Decorated tools gain metadata for
timeout, permissions, and other runtime configuration.
"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Dict, Optional


def tool(
    name: Optional[str] = None,
    *,
    timeout_s: float | None = None,
    permissions: Optional[Dict[str, Any]] = None,
):  # noqa: ANN001
    """Decorator to mark a function as a tool with optional metadata.
    
    Attaches metadata to the function for use by tool runners:
    - __tool_name__: Tool identifier (from name param or function name)
    - __tool_timeout__: Timeout in seconds (for execution limits)
    - __tool_permissions__: ACL dictionary for permission checks
    
    The decorated function can be passed to SimpleToolRunner.register() or
    collected into a registry with registry_from_tools().
    
    Args:
        name: Optional tool identifier. Defaults to function name.
        timeout_s: Optional execution timeout in seconds.
        permissions: Optional dict of permissions/ACL info for the tool.
    
    Returns:
        Decorator function.
    
    Example:
        >>> @tool("my_tool", timeout_s=5.0, permissions={"admin": True})
        ... async def my_tool(query: str) -> str:
        ...     return f"Result for {query}"
        >>> 
        >>> registry = registry_from_tools(my_tool)
        >>> print(registry["my_tool"].__tool_name__)
        "my_tool"
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tname = name or getattr(fn, "__name__", "tool")
        setattr(fn, "__tool_name__", tname)
        setattr(fn, "__tool_timeout__", timeout_s)
        setattr(fn, "__tool_permissions__", permissions or {})

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any):  # noqa: ANN401
            return fn(*args, **kwargs)

        return wrapper

    return _decorator


def registry_from_tools(*funcs: Callable[..., Any]) -> Dict[str, Callable[..., Any]]:
    """Build a tool registry from decorated functions.
    
    Collects decorated functions into a dict mapping tool names to callables.
    Each function should have been decorated with @tool() or have __tool_name__
    attribute set manually.
    
    Args:
        *funcs: One or more functions decorated with @tool.
    
    Returns:
        Dict mapping tool names (str) to callable objects.
    
    Raises:
        None (silently skips functions without __tool_name__).
    
    Example:
        >>> @tool("say_hello")
        ... def greet(name: str) -> str:
        ...     return f"Hello, {name}!"
        ... 
        >>> @tool("say_goodbye")
        ... def farewell() -> str:
        ...     return "Goodbye!"
        ... 
        >>> registry = registry_from_tools(greet, farewell)
        >>> registry["say_hello"]("World")
        "Hello, World!"
    """
    reg: Dict[str, Callable[..., Any]] = {}
    for fn in funcs:
        name = getattr(fn, "__tool_name__", None) or getattr(fn, "__name__", None)
        if name:
            reg[str(name)] = fn
    return reg



__all__ = ["tool", "registry_from_tools"]
