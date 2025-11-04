"""Tool specification and metadata for Nomos tool runners.

This module provides ToolSpec which encapsulates all metadata and behavior
for a tool, including:
- Tool name and description
- Callable function (sync or async)
- Parameter validation schema (Pydantic)
- Timeout and permissions configuration
- Methods to introspect and execute tools

ToolSpec enables tools to be passed around as first-class objects with
full metadata, allowing LLM providers and other components to build
rich context about available tools.
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Optional

from pydantic import BaseModel


@dataclass
class ToolSpec:
    """Complete specification for a tool function.

    Encapsulates a tool's metadata, schema, and executable function in a single
    object. Enables providers and orchestrator to access tool information without
    needing to decompose nested registry structures.

    Attributes:
        name: Unique tool identifier.
        func: The tool function (sync or async callable).
        schema: Pydantic model for parameter validation.
        description: Human-readable description from docstring.
        timeout: Optional execution timeout in seconds.
        permissions: Optional dict of ACL/permission info.

    Example:
        >>> def my_tool(x: int) -> int:
        ...     \"\"\"Increment a number.\"\"\"
        ...     return x + 1
        >>> spec = ToolSpec(
        ...     name="increment",
        ...     func=my_tool,
        ...     schema=...,
        ...     description="Increment a number"
        ... )
        >>> spec.name
        "increment"
        >>> spec.schema.model_fields
        {"x": FieldInfo(...)}
    """

    name: str
    """Unique tool identifier."""

    func: Callable[..., Any]
    """The tool function (sync or async)."""

    schema: type[BaseModel]
    """Pydantic model for parameter validation."""

    description: str = ""
    """Human-readable tool description."""

    timeout: Optional[float] = None
    """Optional execution timeout in seconds."""

    permissions: Dict[str, Any] = field(default_factory=dict)
    """Optional ACL/permission info."""

    def get_args_schema(self) -> type[BaseModel]:
        """Get the Pydantic schema for this tool's arguments.

        Returns:
            Pydantic BaseModel class for parameter validation.
        """
        return self.schema

    def get_args_json_schema(self) -> Dict[str, Any]:
        """Get JSON schema for this tool's arguments.

        Returns a JSON schema representation of the tool's parameters,
        useful for LLM function calling or API documentation.

        Returns:
            JSON schema dict with properties, required fields, etc.
        """
        return self.schema.model_json_schema()

    def get_field_descriptions(self) -> Dict[str, Optional[str]]:
        """Get human-readable descriptions for each parameter.

        Extracts field descriptions from the Pydantic schema.

        Returns:
            Dict mapping parameter name to description (or None).
        """
        schema_dict = self.get_args_json_schema()
        descriptions = {}
        props = schema_dict.get("properties", {})
        for field_name, field_spec in props.items():
            descriptions[field_name] = field_spec.get("description")
        return descriptions

    def get_params_info(self) -> Dict[str, Dict[str, Any]]:
        """Get comprehensive parameter information including types and defaults.

        Returns a dict with parameter names mapped to their type, description,
        and default value (if any).

        Returns:
            Dict mapping parameter name to {type, description, default}.
            Example: {"count": {"type": "integer", "default": 10, "description": "..."}}
        """
        schema_dict = self.get_args_json_schema()
        params = {}
        props = schema_dict.get("properties", {})
        required = schema_dict.get("required", [])

        for pname, pspec in props.items():
            param_info = {
                "type": pspec.get("type", "unknown"),
                "description": pspec.get("description"),
            }
            # Check if parameter has a default value
            if pname not in required and "default" in pspec:
                param_info["default"] = pspec["default"]
            params[pname] = param_info

        return params

    def is_async(self) -> bool:
        """Check if this tool is an async function.

        Returns:
            True if the tool function is async, False otherwise.
        """
        # Check __wrapped__ in case the function is decorated
        unwrapped = getattr(self.func, "__wrapped__", self.func)
        return inspect.iscoroutinefunction(unwrapped)

    def __repr__(self) -> str:
        """Return a string representation of the tool spec."""
        return (
            f"ToolSpec(name={self.name!r}, "
            f"description={self.description!r}, "
            f"timeout={self.timeout}, "
            f"async={self.is_async()})"
        )


__all__ = ["ToolSpec"]
