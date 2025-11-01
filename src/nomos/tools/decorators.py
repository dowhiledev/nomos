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

    Sets attributes used by the SimpleToolRunner: __tool_name__, __tool_timeout__, __tool_permissions__.
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
    """Build a registry mapping tool names to callables from decorated functions."""
    reg: Dict[str, Callable[..., Any]] = {}
    for fn in funcs:
        name = getattr(fn, "__tool_name__", None) or getattr(fn, "__name__", None)
        if name:
            reg[str(name)] = fn
    return reg


__all__ = ["tool", "registry_from_tools"]
