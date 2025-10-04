"""Tool configuration classes."""

from __future__ import annotations

import importlib
import importlib.util
import os
from typing import Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

from ...models.tool import ToolDef, ToolWrapper
from ...utils.utils import convert_camelcase_to_snakecase

# Constants
SUPPORTED_TOOL_TYPES = ["pkg", "crewai", "langchain", "mcp", "api"]


class ExternalTool(BaseModel):
    """Configuration for an external tool.

    Attributes:
        tag: Tag of the external tool (e.g., @pkg/itertools.combinations).
        name: Optional snake_case name of the tool.
        kwargs: Optional keyword arguments for tool initialization.
        map: Optional mapping of method names to API endpoints (for API tools).
    """
    tag: str = Field(..., description="Tag of the external tool")
    name: Optional[str] = Field(None, description="Snake_case name of the tool")
    kwargs: Optional[Dict[str, Union[str, int, float]]] = Field(None, description="Keyword arguments for tool initialization")
    map: Optional[Dict[str, str]] = Field(None, description="Mapping of method names to API endpoints for API tools")

    def get_tool_wrapper(self) -> ToolWrapper:
        """Get the ToolWrapper instance for the external tool.

        Returns:
            ToolWrapper: Configured tool wrapper.

        Raises:
            ValueError: If required fields are missing or tool type is unsupported.
        """
        try:
            tool_type, tool_name = self.tag.split("/", 1)
            tool_type = tool_type.lstrip("@")
        except ValueError:
            raise ValueError(f"Invalid tag format: {self.tag}. Expected '@type/name'.")

        if tool_type == "mcp" and not self.name:
            raise ValueError("For MCP tools, the 'name' field is required.")
        if tool_type == "api" and not self.map and not self.name:
            raise ValueError("For Direct API tools, the 'name' field is required.")

        name = (
            self.name
            or ("Multi-Endpoint API Tool" if self.map else None)
            or convert_camelcase_to_snakecase(tool_name.split(".")[-1])
        )
        if tool_type not in SUPPORTED_TOOL_TYPES:
            raise ValueError(f"Unsupported tool type: {tool_type}. Supported: {SUPPORTED_TOOL_TYPES}")

        return ToolWrapper(
            name=name,
            tool_type=tool_type,
            tool_identifier=tool_name,
            kwargs=self.kwargs,
            map=self.map,
        )

    def __str__(self) -> str:
        return f"ExternalTool(tag={self.tag}, name={self.name})"


class ToolsConfig(BaseModel):
    """Configuration for tools used by the agent.

    Attributes:
        tool_file_paths: List of file paths or module names for tool files.
        external_tools: Optional list of external tools.
        tool_defs: Optional dictionary of tool definitions.
    """
    tool_file_paths: List[str] = Field(
        default_factory=list,
        validation_alias="files",
        serialization_alias="files",
        description="List of file paths or module names for tool files"
    )
    external_tools: Optional[List[ExternalTool]] = Field(
        None,
        validation_alias="ext",
        serialization_alias="ext",
        description="List of external tools"
    )
    tool_defs: Optional[Dict[str, ToolDef]] = Field(
        None,
        validation_alias="defs",
        serialization_alias="defs",
        description="Dictionary of tool definitions"
    )

    model_config = {"populate_by_name": True}

    def _load_tools_from_files(self) -> List[Callable]:
        """Load tools from specified file paths or modules.

        Returns:
            List of tool callables.

        Raises:
            ImportError: If loading fails.
        """
        tools = []
        for tool_file in self.tool_file_paths:
            try:
                if tool_file.endswith(".py"):
                    if not os.path.exists(tool_file):
                        raise FileNotFoundError(f"Tool file '{tool_file}' does not exist.")
                    spec = importlib.util.spec_from_file_location("tool_module", tool_file)
                    if spec is None or spec.loader is None:
                        raise ImportError(f"Could not load module from '{tool_file}'")
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                else:
                    module = importlib.import_module(tool_file)

                module_tools = getattr(module, "tools", [])
                tools.extend(module_tools)
            except (ImportError, FileNotFoundError, AttributeError) as e:
                raise ImportError(f"Failed to load tools from '{tool_file}': {e}")
        return tools

    def _load_external_tools(self) -> List[ToolWrapper]:
        """Load external tools.

        Returns:
            List of ToolWrapper instances.

        Raises:
            ValueError: If loading fails.
        """
        tools = []
        for external_tool in self.external_tools or []:
            try:
                tools.append(external_tool.get_tool_wrapper())
            except ValueError as e:
                raise ValueError(f"Failed to load external tool '{external_tool.tag}': {e}")
        return tools

    def get_tools(self) -> List[Union[Callable, ToolWrapper]]:
        """Load and return all tools based on the configuration.

        Returns:
            List of tool functions or wrappers.
        """
        tools = []
        tools.extend(self._load_tools_from_files())
        tools.extend(self._load_external_tools())
        return tools

    def __str__(self) -> str:
        return f"ToolsConfig(tool_file_paths={len(self.tool_file_paths)}, external_tools={len(self.external_tools or [])})"


__all__ = ["ExternalTool", "ToolsConfig"]