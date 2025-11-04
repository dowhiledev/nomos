"""Decorators and utilities for tool registration and management.

This module provides decorators to mark functions as tools and automatically
build a registry for use by tool runners. Decorated tools gain metadata for
timeout, permissions, and other runtime configuration.

When decorating a function with @tool(), the decorator creates a ToolSpec
containing the function, its schema, and metadata. This enables tools to be
passed as first-class objects with full introspection support.
"""

from __future__ import annotations

import inspect
from functools import wraps
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel, create_model

from .spec import ToolSpec


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


def tool(
    name: Optional[str] = None,
    *,
    description: Optional[str] = None,
    timeout_s: float | None = None,
    permissions: Optional[Dict[str, Any]] = None,
):  # noqa: ANN001
    """Decorator to mark a function as a tool with optional metadata.

    Converts the decorated function into a ToolSpec object and stores it
    as __tool_spec__. The ToolSpec contains:
    - Tool name (from name param or function name)
    - Function callable
    - Pydantic schema for parameter validation
    - Timeout configuration
    - Permissions/ACL info

    The decorated function remains callable for backward compatibility.

    Args:
        name: Optional tool identifier. Defaults to function name.
        description: Optional tool description. If not provided, uses the first
            paragraph of the function's docstring.
        timeout_s: Optional execution timeout in seconds.
        permissions: Optional dict of permissions/ACL info for the tool.

    Returns:
        Decorator function that returns the original callable.

    Example:
        >>> @tool("my_tool", description="My custom tool", timeout_s=5.0)
        ... async def my_tool(query: str) -> str:
        ...     \"\"\"Add more details here.
        ...
        ...     This multi-paragraph docstring only uses the first paragraph.
        ...     \"\"\"
        ...     return f"Result for {query}"
        >>>
        >>> registry = registry_from_tools(my_tool)
        >>> spec = registry["my_tool"]
        >>> print(spec.name)
        "my_tool"
        >>> print(spec.timeout)
        5.0
    """

    def _decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tname = name or getattr(fn, "__name__", "tool")
        schema = _create_tool_schema(fn, tname)
        
        # Use provided description, or extract first paragraph from docstring
        if description is not None:
            tool_description = description
        else:
            doc = fn.__doc__ or ""
            # Extract first paragraph (text before first double newline or end of string)
            first_paragraph = doc.split("\n\n")[0].strip()
            tool_description = first_paragraph

        # Create ToolSpec
        spec = ToolSpec(
            name=tname,
            func=fn,
            schema=schema,
            description=tool_description,
            timeout=timeout_s,
            permissions=permissions or {},
        )

        # Attach spec to function for introspection
        setattr(fn, "__tool_spec__", spec)

        # Also attach legacy attributes for backward compatibility
        setattr(fn, "__tool_name__", tname)
        setattr(fn, "__tool_timeout__", timeout_s)
        setattr(fn, "__tool_permissions__", permissions or {})

        # Preserve async nature of the function
        if inspect.iscoroutinefunction(fn):
            @wraps(fn)
            async def async_wrapper(*args: Any, **kwargs: Any):  # noqa: ANN401
                return await fn(*args, **kwargs)

            # Transfer spec to wrapper
            setattr(async_wrapper, "__tool_spec__", spec)
            setattr(async_wrapper, "__tool_name__", tname)
            setattr(async_wrapper, "__tool_timeout__", timeout_s)
            setattr(async_wrapper, "__tool_permissions__", permissions or {})
            setattr(async_wrapper, "__wrapped__", fn)  # Store original for introspection

            return async_wrapper
        else:
            @wraps(fn)
            def wrapper(*args: Any, **kwargs: Any):  # noqa: ANN401
                return fn(*args, **kwargs)

            # Transfer spec to wrapper
            setattr(wrapper, "__tool_spec__", spec)
            setattr(wrapper, "__tool_name__", tname)
            setattr(wrapper, "__tool_timeout__", timeout_s)
            setattr(wrapper, "__tool_permissions__", permissions or {})
            setattr(wrapper, "__wrapped__", fn)  # Store original for introspection

            return wrapper

    return _decorator


def registry_from_tools(*funcs: Callable[..., Any]) -> Dict[str, ToolSpec]:
    """Build a tool registry from decorated functions.

    Collects ToolSpecs from decorated functions into a dict mapping tool names
    to ToolSpec objects. Each function should have been decorated with @tool()
    which will have set the __tool_spec__ attribute.

    Args:
        *funcs: One or more functions decorated with @tool.

    Returns:
        Dict mapping tool names (str) to ToolSpec objects.

    Raises:
        None (silently skips functions without __tool_spec__).

    Example:
        >>> @tool("say_hello")
        ... def greet(name: str) -> str:
        ...     \"\"\"Greet someone.\"\"\"
        ...     return f"Hello, {name}!"
        ...
        >>> @tool("say_goodbye")
        ... def farewell() -> str:
        ...     \"\"\"Say goodbye.\"\"\"
        ...     return "Goodbye!"
        ...
        >>> registry = registry_from_tools(greet, farewell)
        >>> registry["say_hello"].name
        "say_hello"
        >>> registry["say_hello"].description
        "Greet someone."
    """
    reg: Dict[str, ToolSpec] = {}
    for fn in funcs:
        # Prefer __tool_spec__ (new style), fall back to legacy attributes
        spec = getattr(fn, "__tool_spec__", None)
        if spec:
            reg[spec.name] = spec
        else:
            # Legacy: only name is available, skip
            pass
    return reg


__all__ = ["tool", "registry_from_tools"]
