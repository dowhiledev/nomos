"""Tools module for Nomos — tool registration, execution, and specification.

This module provides:
- ToolSpec: Encapsulation of tool metadata and callable
- @tool decorator: Mark functions as tools with metadata
- registry_from_tools: Collect decorated tools into a registry
- SimpleToolRunner: Execute registered tools with validation and isolation
- ToolExecutionContext: Context for tools to emit events during execution
"""

from .spec import ToolSpec
from .decorators import tool, registry_from_tools
from .runner import SimpleToolRunner, ToolExecutionContext

__all__ = [
    "ToolSpec",
    "tool",
    "registry_from_tools",
    "SimpleToolRunner",
    "ToolExecutionContext",
]
