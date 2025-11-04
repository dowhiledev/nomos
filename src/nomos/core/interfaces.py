"""Core protocol definitions for the Nomos orchestrator.

This module defines the primary interfaces (Protocols) that the orchestrator
depends on. These interfaces enable pluggable implementations of LLM providers,
tool runners, and storage backends. Implementations should follow these contracts
to ensure compatibility with the event-sourced orchestration engine.

The four core interfaces are:
- LLMProvider: Converts messages to decisions via streaming language models
- ToolRunner: Executes user-defined functions and emits execution frames
- EventStore: Persists and retrieves session events (append-only log)
- CheckpointStore: Saves and restores session state for interruption/replay
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Protocol, Union, TYPE_CHECKING
from .types import ProviderSchema, ProviderFrame, ToolFrameUnion, ToolArgs
from .schemas import Message, Checkpoint
from .events import SessionEvent

if TYPE_CHECKING:
    from nomos.tools.spec import ToolSpec


class LLMProvider(Protocol):
    """Protocol for language model provider adapters.

    Implementations of this protocol handle communication with language models
    to generate decisions, stream tokens, and produce structured outputs.
    Adapters are responsible for:
    - Building context-aware prompts with node instructions and available routing
    - Streaming tokens and decision frames to the orchestrator
    - Converting provider-native formats to Nomos decision schemas

    Example:
        >>> provider = OpenAI(model="gpt-4o-mini")
        >>> messages = [Message(role="user", content="Hello")]
        >>> async for frame in provider.stream_decision(messages, schema=None):
        ...     print(frame)
    """

    def build_decision_messages(
        self,
        agent_spec: Any,  # AgentSpec - type: ignore for circular imports
        current_node_id: str,
        available_tools: Dict[
            str, Any
        ],  # Dict[str, ToolSpec] - use Any to avoid circular import
        base_messages: List[Union[Message, Dict[str, Any]]],
    ) -> List[Union[Message, Dict[str, Any]]]:
        """Build context-aware messages for decision-making.

        This method constructs the complete message list that will be sent to
        the LLM, typically including:
        - System prompts with node instructions
        - Available routing options (next steps/targets)
        - Available tools with their descriptions and parameter schemas
        - Conversation history and context

        The available_tools dict maps tool names to ToolSpec objects, allowing
        the provider to include rich tool metadata in the prompt:
        - Tool name and description
        - Parameter schemas (JSON schema format)
        - Timeout and permission information

        Args:
            agent_spec: The compiled AgentSpec containing nodes, edges, and routing info.
            current_node_id: The ID of the current node in the graph.
            available_tools: Dict mapping tool names to ToolSpec objects.
                Each ToolSpec contains:
                    - name: Tool identifier
                    - description: Human-readable description
                    - schema: Pydantic model for parameters
                    - timeout: Optional execution timeout
                    - permissions: Optional ACL info
                    - get_args_json_schema(): Method to get JSON schema
            base_messages: Existing message history to append instructions to.

        Returns:
            Complete message list ready for LLM consumption, typically with
            system prompts prepended and routing/tool info injected.
        """
        ...

    def stream_decision(
        self, messages: List[Union[Message, Dict[str, Any]]], schema: ProviderSchema
    ) -> AsyncIterator[ProviderFrame]:
        """Stream decision frames from the LLM.

        This generator should yield one or more frames during LLM processing:
        - TokenFrame objects for incremental token emission
        - DecisionFrame with final decision (RESPOND, TOOL_CALL, or MOVE)

        The orchestrator will collect these frames to determine the next action.

        Args:
            messages: Complete message list for the LLM.
            schema: Optional response schema for structured output validation.

        Yields:
            ProviderFrame objects (TokenFrame or DecisionFrame).

        Raises:
            Exception: Provider-specific errors should be raised with clear messages.
        """
        ...

    def stream_generate(
        self, messages: List[Union[Message, Dict[str, Any]]]
    ) -> AsyncIterator[ProviderFrame]:
        """Stream generation without decision routing.

        Used for pure text generation without invoking the decision logic.
        Typically yields TokenFrame objects for streaming text output.

        Args:
            messages: Message list for generation.

        Yields:
            ProviderFrame objects (typically TokenFrame only).
        """
        ...


class ToolRunner(Protocol):
    """Protocol for tool execution runners.

    Implementations handle invocation of user-defined tools, parameter validation,
    event emission, and error handling. The runner bridges between the orchestrator's
    tool calls and the actual Python functions.

    Features:
    - Tool introspection via get_tools() returning ToolSpec objects with full metadata
    - Schema validation of tool arguments
    - Event streaming (started, progress, stdout, completed, error)
    - Timeout and cancellation support
    - Execution mode options (inline, thread, process)

    Example:
        >>> runner = SimpleToolRunner()
        >>> runner.register("my_tool", my_tool_func)
        >>> async for frame in runner.run("my_tool", {"arg": "value"}, ctx):
        ...     print(frame)
        >>> tools = runner.get_tools()
        >>> print(tools["my_tool"].description)
    """

    def get_tools(self) -> Dict[str, ToolSpec]:
        """Get all registered tools with full metadata.

        Returns a dict mapping tool names to ToolSpec objects, enabling
        providers and other components to access tool information including
        name, description, schema, timeout, and permissions.

        This method is used by LLM providers to build context-aware prompts with
        tool descriptions and parameter schemas, allowing the model to understand
        what tools are available and how to call them.

        Returns:
            Dict mapping tool names (str) to ToolSpec objects. Each ToolSpec contains:
                - name: Tool identifier
                - description: Human-readable description from docstring
                - schema: Pydantic BaseModel for parameter validation
                - timeout: Optional execution timeout in seconds
                - permissions: Optional ACL/permission info
                - func: The callable function (for execution)

        Example:
            >>> runner = SimpleToolRunner()
            >>> @runner.tool("greet")
            ... def greet(name: str) -> str:
            ...     \"\"\"Greet someone.\"\"\"
            ...     return f"Hello, {name}!"
            >>> tools = runner.get_tools()
            >>> spec = tools["greet"]
            >>> spec.name
            "greet"
            >>> spec.description
            "Greet someone."
            >>> spec.get_args_json_schema()
            {"type": "object", "properties": {"name": {"type": "string"}}, ...}
        """
        ...

    def run(
        self, tool_name: str, args: ToolArgs, ctx: Dict[str, Any]
    ) -> AsyncIterator[ToolFrameUnion]:
        """Execute a tool and stream execution frames.

        Implementations should:
        1. Look up the tool by name in their registry
        2. Validate args against the tool's schema
        3. Emit a ToolStarted frame
        4. Execute the tool (respecting ctx.cancel_event)
        5. Emit progress/stdout frames as appropriate
        6. Emit ToolCompleted or ToolError frame

        Args:
            tool_name: Unique identifier for the tool to execute.
            args: Keyword arguments for the tool, validated against schema.
            ctx: Execution context with session info and cancellation signal.

        Yields:
            ToolFrameUnion objects documenting execution progress and result.

        Raises:
            KeyError: If tool_name is not registered.
            ValueError: If args don't match tool schema.
        """
        ...


class EventStore(Protocol):
    """Protocol for append-only event storage.

    Implementations provide persistence for the session event log. Events are
    immutable and stored in append-only fashion, enabling:
    - Complete session replay from events
    - Deterministic reconstruction of state
    - Event-sourced debugging and audit trails

    Implementations should ensure:
    - Atomicity: All events in a batch are written together
    - Ordering: Events maintain insert order and session sequence
    - Durability: Events survive service restarts (for prod implementations)

    Example:
        >>> store = InMemoryEventStore()
        >>> await store.append(session_id, [event1, event2])
        >>> events = await store.read_by_session(session_id)
        >>> async for ev in store.subscribe(session_id):
        ...     print(ev.type)
    """

    async def append(self, session_id: str, events: List[SessionEvent]) -> None:
        """Append events to the session log.

        Atomically appends a batch of events to the session's append-only log.
        Implementations may assign event IDs for SSE resume capability.

        Args:
            session_id: Unique session identifier.
            events: List of SessionEvent objects to append.

        Raises:
            Exception: Storage errors (connection, permission, etc).
        """
        ...

    async def read_by_session(self, session_id: str) -> List[SessionEvent]:
        """Read all events for a session.

        Retrieves the complete event history in append order. Used for
        replaying a session or migrating data.

        Args:
            session_id: Unique session identifier.

        Returns:
            List of all SessionEvent objects for the session, in order.

        Raises:
            KeyError: If session_id doesn't exist.
        """
        ...

    def subscribe(self, session_id: str) -> AsyncIterator[SessionEvent]:
        """Subscribe to new events for a session.

        Returns an async iterator that yields events as they are appended.
        Used for real-time event streaming (e.g., SSE, WebSocket).

        Args:
            session_id: Unique session identifier.

        Yields:
            SessionEvent objects as they are appended.
        """
        ...


class CheckpointStore(Protocol):
    """Protocol for checkpoint persistence.

    Implementations store and restore checkpoints for session interruption,
    resumption, and deterministic replay. Checkpoints capture the session state
    at node boundaries, allowing clean resumption without recomputation.

    Implementations should support:
    - Multiple checkpoints per session (by checkpoint_id)
    - Fast loading for resume operations
    - Optional versioning for schema evolution

    Example:
        >>> store = InMemoryCheckpointStore()
        >>> cp = Checkpoint(id="cp1", node_id="gather_input", data={...})
        >>> await store.save(session_id, cp)
        >>> restored = await store.load(session_id, "cp1")
    """

    async def save(self, session_id: str, checkpoint: Checkpoint) -> None:
        """Save a checkpoint for a session.

        Stores session state at a node boundary. Multiple checkpoints can
        exist for a session, each identified by checkpoint.id.

        Args:
            session_id: Unique session identifier.
            checkpoint: Checkpoint object with id, node_id, and state data.

        Raises:
            Exception: Storage errors (connection, permission, etc).
        """
        ...

    async def load(self, session_id: str, checkpoint_id: str) -> Checkpoint:
        """Load a checkpoint for a session.

        Retrieves a previously saved checkpoint. Used when resuming a session
        from an interruption point.

        Args:
            session_id: Unique session identifier.
            checkpoint_id: Specific checkpoint identifier.

        Returns:
            The Checkpoint object with restored state.

        Raises:
            KeyError: If checkpoint_id doesn't exist for the session.
        """
        ...


__all__ = [
    "LLMProvider",
    "ToolRunner",
    "EventStore",
    "CheckpointStore",
]
