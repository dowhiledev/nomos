# Code Quality Improvements Tracking

**Date Started:** 2025-11-03  
**Focus:** Docstring coverage, type safety improvements, and better interfaces for client usage.

## Summary

This document tracks improvements in code quality across the Nomos project, particularly focusing on:
1. **Docstring Coverage** - Adding comprehensive docstrings following Google/VSCode style
2. **Type Safety** - Identifying and replacing generic `Dict[str, Any]` with proper Pydantic models
3. **Interface Clarity** - Ensuring public APIs have clear, developer-first documentation

---

## Type Safety Issues & Improvements

### Priority 1: Core Types That Need Better Structure

#### 1. **src/nomos/core/types.py**
- **Current Status:** Has type aliases but lacks documentation
- **Issues:**
  - `ToolArgs: TypeAlias = Dict[str, Any]` - Should validate against tool schemas
  - `ProviderFrame: TypeAlias = Union[DecisionFrame, TokenFrame, Dict[str, Any]]` - The `Dict[str, Any]` fallback should be removed; all frames should be properly typed
- **Improvement:** Create strict ProviderFrameModel with all variants
- **Pydantic Model Candidates:**
  - `ProviderFrameStrict` - Remove dict fallback
  - `ToolCallArgs` - Wrap ToolArgs with validation

#### 2. **src/nomos/core/orchestrator.py**
- **Current Status:** Verbose but uses many untyped dicts
- **Issues:**
  - `_format_messages_table(messages: List[Dict[str, Any]])` - Should be `List[Message]`
  - `_format_decision(decision_data: Dict[str, Any])` - Should be `Decision`
  - Internal state management uses untyped dicts
  - `materialize_state()` returns `Dict[str, Any]` but could return `SessionState`
- **Improvements:**
  - Enforce `Message` and `Decision` types throughout
  - Create `OrchestratorState` Pydantic model for internal state
  - Type all decision/routing operations with `Decision` model

#### 3. **src/nomos/core/interfaces.py**
- **Current Status:** Protocol definitions use `Dict[str, Any]` for flexibility
- **Issues:**
  - `LLMProvider.build_decision_messages()` takes `List[Union[Message, Dict[str, Any]]]` - Should normalize to `List[Message]`
  - `ToolRunner.run()` uses `Dict[str, Any]` for args - Should use typed `ToolArgs` or schema validation
  - All `Dict[str, Any]` fields in protocols make it hard to enforce contracts
- **Improvements:**
  - Replace `Dict[str, Any]` with `Message` in LLMProvider
  - Require tool schema validation in ToolRunner
  - Consider making protocols stricter or providing typed decorators

#### 4. **src/nomos/core/schemas.py**
- **Current Status:** Good structure but some flexibility issues
- **Issues:**
  - `ToolCall.tool_kwargs: dict` and `tool_kwargs_parsed: Optional[dict]` - Should be `Dict[str, Any]` with validation
  - `Checkpoint.data: Dict[str, Any]` - Should have schema validation or subtyping
  - `SessionInput.messages` allows mixed `Union[Message, Dict[str, Any]]` - Should normalize to `Message`
- **Improvements:**
  - Replace raw `dict` with typed versions
  - Add JSON schema validation for tool_kwargs
  - Create `CheckpointData` model with versioning

#### 5. **src/nomos/graph/runtime.py**
- **Current Status:** Flexible but untyped
- **Issues:**
  - `Step.tools: Optional[List[object]]` - Should be `List[Callable]` with better type hints
  - No validation of YAML-loaded steps against schemas
- **Improvements:**
  - Create `ToolRegistry` Pydantic model
  - Validate loaded steps with `Step` schema

### Priority 2: Provider & Tool Adapters

#### 6. **src/nomos/llms/openai.py**
- **Current Status:** Uses `Dict[str, Any]` for message construction
- **Issues:**
  - `_to_openai_messages()` returns `List[Dict[str, Any]]` - Should be typed OpenAI schema
  - `_to_openai_content()` uses untyped parts
  - `build_decision_messages()` builds system message as dict array
- **Improvements:**
  - Create `OpenAIMessage` and `OpenAIContent` Pydantic models
  - Use discriminated unions for message types

#### 7. **src/nomos/tools/runner.py**
- **Current Status:** Uses generic dicts for tool schemas
- **Issues:**
  - `ToolInfo.schema: type[BaseModel]` - Good, but not enforced at registration
  - `_create_tool_schema()` creates models dynamically - Validation is weak
  - Tool execution context uses `List[Dict[str, Any]]` for events
- **Improvements:**
  - Create `ToolSchema` wrapper model
  - Use `ToolFrame` (already exists) instead of generic dicts

#### 8. **src/nomos/tools/decorators.py**
- **Current Status:** Minimal typing
- **Issues:**
  - `permissions: Optional[Dict[str, Any]]` - Should have schema
  - `registry_from_tools()` returns untyped dict
- **Improvements:**
  - Create `ToolPermissions` Pydantic model
  - Create `ToolRegistry` model with validation

### Priority 3: Server & Storage

#### 9. **src/nomos/server/__init__.py**
- **Current Status:** FastAPI app uses generic dicts
- **Issues:**
  - Request/response bodies should be Pydantic models throughout
  - Event SSE payload handling uses untyped dicts
- **Improvements:**
  - Create request/response models (already have some)
  - Ensure all endpoints return typed responses

#### 10. **src/nomos/core/store/\*.py**
- **Current Status:** Uses `Dict[str, Any]` for generic storage
- **Issues:**
  - Checkpoint stores use generic dicts
  - No versioning or schema evolution support
- **Improvements:**
  - Create `StoredCheckpoint` model with metadata
  - Add version field for migration support

### Priority 4: Examples & Utilities

#### 11. **examples/\*.py**
- **Current Status:** Tool functions use basic types
- **Issues:**
  - `@runner.tool()` decorated functions need better type hints
  - Return types are often strings instead of structured data
- **Improvements:**
  - Standardize on `ToolResult` Pydantic model
  - Use proper return types for all tools

#### 12. **src/nomos/core/observe.py**
- **Current Status:** Uses generic dicts for metrics
- **Issues:**
  - `metrics_snapshot()` returns `Dict[str, Dict[str, float]]` - Could be a model
  - `span()` and `measure()` context managers lack typing
- **Improvements:**
  - Create `MetricsSnapshot` Pydantic model
  - Better type hints for context managers

---

## New Pydantic Models to Create

### Recommended Additions

```python
# In schemas.py or new dedicated modules

class ToolSchema(BaseModel):
    """Validated tool parameter schema."""
    name: str
    params: Dict[str, Any]
    required: List[str] = Field(default_factory=list)

class ToolResult(BaseModel):
    """Standardized tool execution result."""
    tool_name: str
    status: Literal["success", "error", "timeout"]
    data: Any
    timestamp: float

class DecisionContext(BaseModel):
    """Context for LLM decision-making."""
    node_id: str
    node_prompt: str
    available_routes: List[EdgeSpec]
    available_tools: List[str]
    messages: List[Message]

class MetricsSnapshot(BaseModel):
    """Structured metrics snapshot."""
    counters: Dict[str, int]
    latencies: Dict[str, List[float]]
    timestamp: float

class OrchestratorCheckpoint(BaseModel):
    """Enhanced checkpoint with metadata."""
    id: str
    version: int
    session_id: str
    node_id: Optional[str]
    data: Dict[str, Any]
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
```

---

## Docstring Improvements Completed

### Core Module (`src/nomos/core/`)

- [x] `__init__.py` - Exported main Orchestrator
- [x] `events.py` - Event types and SessionEvent model
- [x] `interfaces.py` - Protocol definitions (LLMProvider, ToolRunner, EventStore, CheckpointStore)
- [x] `schemas.py` - Message, ToolCall, Decision models
- [x] `state.py` - SessionState model
- [x] `types.py` - Type aliases and ToolContext
- [x] `observe.py` - Observability utilities
- [x] `redaction.py` - Redaction utilities
- [x] `replay.py` - State projection utilities
- [x] `tool_events.py` - Tool frame models
- [x] `orchestrator.py` - Session orchestrator implementation
- [ ] `store/memory.py` - InMemoryEventStore
- [ ] `store/checkpoint_memory.py` - InMemoryCheckpointStore

### Graph Module (`src/nomos/graph/`)

- [ ] `spec.py` - AgentSpec, NodeSpec, EdgeSpec
- [ ] `builder.py` - GraphBuilder DSL
- [ ] `runtime.py` - Graph, Step, Transition runtime
- [ ] `prompt.py` - Prompt generation utilities

### LLM Providers (`src/nomos/llms/`)

- [ ] `openai.py` - OpenAI provider adapter

### Tools Module (`src/nomos/tools/`)

- [ ] `decorators.py` - @tool decorator and registry
- [ ] `runner.py` - SimpleToolRunner implementation

### Server (`src/nomos/server/`)

- [ ] `__init__.py` - FastAPI app factory

### Examples (`examples/`)

- [ ] `barista.py` - Full barista example
- [ ] `barista_yaml.py` - YAML-based barista example
- [ ] `__init__.py` - Package initialization

---

## Current Docstring Style Used

The project follows **Google-style docstrings** (compatible with VSCode IntelliSense):

### Example Format

```python
def function_name(param1: str, param2: int) -> Dict[str, Any]:
    """Brief one-line description.
    
    Longer description explaining the function's purpose, behavior,
    and any important details or side effects.
    
    Args:
        param1: Description of param1.
        param2: Description of param2 (default: some value).
    
    Returns:
        Description of return value and its structure.
    
    Raises:
        ValueError: When param2 is negative.
        KeyError: When a required key is missing.
    
    Example:
        >>> result = function_name("test", 42)
        >>> print(result["key"])
    """
```

---

## Testing & Validation Strategy

1. **Type Checking**: Use `mypy` or `pyright` to validate new type hints
2. **Runtime Validation**: Ensure Pydantic models validate at runtime
3. **Breaking Changes**: Document any API changes in migration guide
4. **Examples**: Update examples to use new typed interfaces
5. **Performance**: Verify no performance regressions from added validation

---

## Related Files

- `AGENTS.md` - Engineering guide with code style requirements
- `IMPLEMENTATION_PLAN.md` - Overall implementation progress
- `BRAINSTORM.md` - Domain and architecture decisions

---

## Next Steps

1. ✅ Create this tracking document
2. Add comprehensive docstrings to all public interfaces
3. Create new Pydantic models for type safety
4. Update type hints in existing functions
5. Add mypy validation to CI/CD
6. Update examples to showcase typed interfaces
7. Document migration path for any breaking changes

