# ToolSpec Implementation Summary

## Overview
Implemented a comprehensive `ToolSpec` system that converts tool callables into first-class objects with full metadata, enabling LLM providers to access rich tool information including descriptions, parameter schemas, timeouts, and permissions.

## Key Changes

### 1. Created `ToolSpec` Class (`src/nomos/tools/spec.py`)
A dataclass that encapsulates complete tool metadata:
- **name**: Unique tool identifier
- **func**: The callable function (sync or async)
- **schema**: Pydantic BaseModel for parameter validation
- **description**: Human-readable description from docstring
- **timeout**: Optional execution timeout in seconds
- **permissions**: Optional ACL/permission info

**Methods:**
- `get_args_schema()`: Returns the Pydantic schema
- `get_args_json_schema()`: Returns JSON schema representation
- `get_field_descriptions()`: Returns parameter descriptions
- `is_async()`: Checks if tool is async

### 2. Updated `@tool` Decorator (`src/nomos/tools/decorators.py`)
- Now creates `ToolSpec` objects instead of just setting attributes
- Stores `ToolSpec` as `__tool_spec__` attribute on decorated functions
- Maintains backward compatibility with legacy `__tool_*__` attributes
- Added `_create_tool_schema()` helper function for parameter introspection

### 3. Updated `registry_from_tools()` (`src/nomos/tools/decorators.py`)
- Returns `Dict[str, ToolSpec]` instead of `Dict[str, Callable]`
- Extracts ToolSpec from decorated functions
- Full metadata preserved in registry

### 4. Enhanced `SimpleToolRunner` (`src/nomos/tools/runner.py`)
- **Registry Storage**: Changed `_registry` to store `ToolSpec` objects
- **New `get_tools()` Method**: Returns `Dict[str, ToolSpec]` with full metadata
- **Backward Compatibility**: 
  - Accepts both `ToolSpec` objects and callables in registry dict
  - Auto-converts callables to `ToolSpec` objects
  - Maintains support for old decorator metadata
- Updated `run()` and `_execute_tool()` to use ToolSpec attributes

### 5. Updated `ToolRunner` Protocol (`src/nomos/core/interfaces.py`)
- Added `get_tools()` method to the protocol
- Allows providers and orchestrator to access tool metadata
- Comprehensive documentation of ToolSpec structure

### 6. Updated `LLMProvider` Protocol (`src/nomos/core/interfaces.py`)
- Changed `build_decision_messages()` signature:
  - **Before**: `allowed_tools: List[str]` (tool names only)
  - **After**: `available_tools: Dict[str, ToolSpec]` (full metadata)
- Enables rich tool documentation in system prompts

### 7. Updated `OpenAI` Provider (`src/nomos/llms/openai.py`)
- Enhanced `build_decision_messages()` to use ToolSpec objects
- Includes tool descriptions and parameter schemas in system prompt
- Format: `tool_name: description` with `Parameters: name (type), ...`
- Provides LLM with comprehensive tool context

### 8. Updated `Orchestrator` (`src/nomos/core/orchestrator.py`)
- Modified to call `runner.get_tools()` to get ToolSpec objects
- Filters tools by node-specific allowed tools list
- Passes `Dict[str, ToolSpec]` to provider's `build_decision_messages()`

### 9. Created `tools/__init__.py`
- Exports `ToolSpec`, `tool`, `registry_from_tools`, `SimpleToolRunner`, `ToolExecutionContext`
- Provides clean public API for tools module

## Backward Compatibility
- Old callable-based registries still work
- Automatic conversion from callables to `ToolSpec`
- Legacy `__tool_*__` attributes still supported
- Existing code using `@runner.tool` decorator continues to work

## Benefits
1. **Rich Tool Metadata**: LLMs now have access to tool descriptions and parameter schemas
2. **Better Prompts**: System prompts can include parameter types and usage info
3. **Type Safety**: ToolSpec provides structured access to tool information
4. **Extensibility**: Easy to add more metadata (e.g., tags, categories)
5. **Introspection**: Tools can be examined and validated at runtime

## Example Usage

```python
from nomos.tools import SimpleToolRunner, tool, registry_from_tools

# Using decorator
runner = SimpleToolRunner()

@runner.tool("add")
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# Get tools with full metadata
tools = runner.get_tools()
spec = tools["add"]
print(spec.name)           # "add"
print(spec.description)    # "Add two numbers together."
print(spec.get_args_json_schema())
# {
#   "type": "object",
#   "properties": {
#     "a": {"type": "integer"},
#     "b": {"type": "integer"}
#   },
#   "required": ["a", "b"]
# }

# Using registry_from_tools
@tool("multiply", timeout_s=5.0)
def multiply(x: int, y: int) -> int:
    """Multiply two numbers."""
    return x * y

registry = registry_from_tools(multiply)
# registry is Dict[str, ToolSpec], not Dict[str, Callable]
```

## Testing
- All 43 existing tests pass
- New integration tests verify:
  - ToolSpec creation and metadata extraction
  - Backward compatibility with old registries
  - Provider integration with tool specs
  - JSON schema generation for tool parameters

## Files Modified
- `src/nomos/tools/spec.py` (NEW)
- `src/nomos/tools/__init__.py` (NEW)
- `src/nomos/tools/decorators.py` (MODIFIED)
- `src/nomos/tools/runner.py` (MODIFIED)
- `src/nomos/core/interfaces.py` (MODIFIED)
- `src/nomos/llms/openai.py` (MODIFIED)
- `src/nomos/core/orchestrator.py` (MODIFIED)
