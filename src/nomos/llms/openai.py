"""OpenAI provider adapter implementing the LLMProvider protocol.

This adapter integrates OpenAI's chat completion models with the Nomos orchestrator.
It handles:
- Converting Nomos Message objects to OpenAI format
- Building context-aware system prompts with routing and tool info
- Streaming tokens and decision frames during generation
- Parsing structured Decision responses (JSON)
- Fallback handling for different OpenAI API modes

The adapter prefers structured outputs (via response_format=Decision) but falls
back to JSON mode streaming for compatibility.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, List, Optional, Union
import json

from nomos.core.events import EventType, TokenFrame, DecisionFrame
from nomos.core.schemas import Message, Decision
from pydantic import BaseModel
from nomos.core.interfaces import LLMProvider
from nomos.core.types import ProviderSchema, ProviderFrame

if TYPE_CHECKING:
    from nomos.graph import AgentSpec
    from openai import AsyncOpenAI


async def _async_iter_wrapper(sync_iter):  # noqa: ANN001
    """Wrap a sync iterator to be async-iterable.

    Allows using sync iterators with async for loops by yielding
    items one at a time in an async generator.

    Args:
        sync_iter: A synchronous iterator to wrap.

    Yields:
        Items from the sync iterator.
    """
    for item in sync_iter:
        yield item


def _to_openai_content(parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:  # noqa: ANN401
    """Convert Nomos content parts to OpenAI message content array.

    Transforms rich content structures (text, images, etc) into OpenAI's
    expected message format. Handles unknown types gracefully by falling
    back to text representation.

    Args:
        parts: List of content part dicts with 'type' and 'data' fields.

    Returns:
        List of OpenAI message content objects.

    Example:
        >>> parts = [
        ...     {"type": "text", "data": "Hello"},
        ...     {"type": "image", "data": {"url": "https://example.com/img.png"}}
        ... ]
        >>> openai_content = _to_openai_content(parts)
        >>> openai_content[0]["type"]
        "text"
        >>> openai_content[1]["type"]
        "image_url"
    """
    out: List[Dict[str, Any]] = []
    for p in parts:
        ptype = p.get("type")
        if ptype == "text":
            out.append({"type": "text", "text": p.get("data", "")})
        elif ptype == "image":
            data = p.get("data", {}) or {}
            url = data.get("url") or data
            out.append({"type": "image_url", "image_url": {"url": url}})
        else:
            # unknown types fall back to text
            out.append({"type": "text", "text": str(p.get("data"))})
    return out


def _to_openai_messages(
    messages: List[Union[Message, Dict[str, Any]]],
) -> List[Dict[str, Any]]:  # noqa: ANN401
    """Convert Nomos Message objects to OpenAI message format.

    Normalizes mixed Message and dict inputs to a consistent OpenAI format.
    Handles both plain text and multi-part content.

    Args:
        messages: List of Message objects or dicts.

    Returns:
        List of dicts in OpenAI message format with 'role' and 'content'.

    Example:
        >>> msgs = [Message(role="user", content="Hello, OpenAI!")]
        >>> oai_msgs = _to_openai_messages(msgs)
        >>> oai_msgs[0]["role"]
        "user"
        >>> oai_msgs[0]["content"]
        "Hello, OpenAI!"
    """
    # Convert typed Messages to OpenAI message format
    oai: List[Dict[str, Any]] = []
    for m in messages:
        # Convert dict messages to Message objects if needed
        if isinstance(m, dict):
            m = Message.model_validate(m)
        role = m.role
        content = m.content
        if isinstance(content, list):
            raw_parts = [
                c.model_dump() if hasattr(c, "model_dump") else c for c in content
            ]
            oai.append({"role": role, "content": _to_openai_content(raw_parts)})
        else:
            oai.append({"role": role, "content": content})
    return oai


class OpenAI(LLMProvider):
    """OpenAI language model provider adapter.

    Implements the LLMProvider protocol using OpenAI's chat completion API.
    Supports both structured outputs (Decision format) and JSON mode streaming.

    Attributes:
        model: OpenAI model identifier (default: "gpt-4o-mini").
        client: Optional pre-configured OpenAI client (for testing or custom setup).

    Example:
        >>> from openai import OpenAI as OAIClient
        >>> provider = OpenAI(model="gpt-4o", client=OAIClient())
        >>> async for frame in provider.stream_decision(messages, schema):
        ...     if frame["type"] == "decision.completed":
        ...         print(f"Decision: {frame['data']['action']}")
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        client: Optional[AsyncOpenAI] = None,
    ) -> None:
        """Initialize the OpenAI provider.

        Args:
            model: OpenAI model ID to use (e.g., "gpt-4o", "gpt-4o-mini").
            client: Optional OpenAI AsyncOpenAI client instance. If not provided, creates
                one lazily on first use (requires OPENAI_API_KEY env var).
        """
        self._model = model
        self._client = client

    def build_decision_messages(
        self,
        agent_spec: AgentSpec,
        current_node_id: str,
        available_tools: Dict[str, Any],
        base_messages: List[Union[Message, Dict[str, Any]]],
    ) -> List[Union[Message, Dict[str, Any]]]:
        """Build context-aware messages for decision-making.

        Constructs a complete message list by prepending system prompts that explain:
        - The agent's role and decision-making format
        - Current node instructions
        - Available routing options (next nodes)
        - Available tools with detailed descriptions and parameter schemas

        The available_tools dict contains ToolSpec objects with full metadata,
        allowing rich tool documentation in the system prompt.

        Args:
            agent_spec: Compiled AgentSpec with nodes and edges.
            current_node_id: Current node ID for routing context.
            available_tools: Dict mapping tool names to ToolSpec objects with metadata.
            base_messages: Existing message history to append instructions to.

        Returns:
            Complete message list with system prompts prepended.

        Example:
            >>> spec = AgentSpec(...)
            >>> tools = runner.get_tools()  # Dict[str, ToolSpec]
            >>> msgs = [Message(role="user", content="Hello")]
            >>> result = provider.build_decision_messages(spec, "start", tools, msgs)
            >>> result[0]["role"]
            "system"
        """
        # Find the current node
        current_node = None
        for node in agent_spec.nodes:
            if node.id == current_node_id:
                current_node = node
                break

        if not current_node:
            # Fallback if node not found
            return base_messages

        # Get edges from current node
        edges = [edge for edge in agent_spec.edges if edge.from_id == current_node_id]

        # Build routes description
        routes_desc = []
        for edge in edges:
            condition = edge.condition or f"move to {edge.to_id}"
            routes_desc.append(f"- if '{condition}' then -> {edge.to_id}")
        routes_txt = "\n".join(routes_desc)

        # Build tools description with full metadata
        tools_desc = []
        for tool_name, tool_spec in available_tools.items():
            # Format: tool_name: description
            # Then include JSON schema for parameters
            desc_line = f"- {tool_name}"
            if tool_spec.description:
                desc_line += f": {tool_spec.description}"
            tools_desc.append(desc_line)
            
            # Include parameter schema with defaults
            try:
                params_info = tool_spec.get_params_info()
                if params_info:
                    param_parts = []
                    for pname, pinfo in params_info.items():
                        ptype = pinfo.get("type", "unknown")
                        param_str = f"{pname} ({ptype})"
                        # Add default if present
                        if "default" in pinfo:
                            param_str += f" = {pinfo['default']}"
                        param_parts.append(param_str)
                    params_str = ", ".join(param_parts)
                    tools_desc.append(f"  Parameters: {params_str}")
            except Exception:
                # If schema extraction fails, skip detailed params
                pass

        tools_txt = "\n".join(tools_desc)

        # Build system message
        system_content = [
            {
                "type": "text",
                "data": (
                    "You are an agent deciding the next step or tool call based on the current node.\n"
                    "Output strictly one JSON object with reasoning and decision. Valid shapes:\n"
                    '- MOVE: {"reasoning": ["step1", "step2"], "action":"MOVE","step_id":<one of allowed targets>}\n'
                    '- TOOL_CALL: {"reasoning": ["step1"], "action":"TOOL_CALL","tool_call":{"tool_name":<name>,"tool_kwargs":{...}}}\n'
                    '- RESPOND: {"reasoning": ["step1"], "action":"RESPOND","response":<text>}\n'
                    "Decide the next action based on the current instructions, available routes, and conversation history.\n"
                    "If a route condition is satisfied, use MOVE. Otherwise, use TOOL_CALL or RESPOND as appropriate.\n"
                    "No commentary, no markdown, no code fences."
                ),
            }
        ]

        if current_node.prompt:
            system_content.append(
                {"type": "text", "data": f"\nInstructions: {current_node.prompt}"}
            )

        if routes_txt:
            system_content.append(
                {"type": "text", "data": f"\nAvailable Routes:\n{routes_txt}"}
            )

        if tools_txt:
            system_content.append(
                {"type": "text", "data": f"\nAvailable Tools:\n{tools_txt}"}
            )

        sys_msg = {
            "role": "system",
            "content": system_content,
        }

        return [sys_msg] + base_messages

    async def stream_decision(
        self, messages: List[Union[Message, Dict[str, Any]]], schema: ProviderSchema
    ) -> AsyncIterator[ProviderFrame]:
        """Stream decision frames from OpenAI chat completions.

        Attempts to use structured outputs (Decision format) first, then falls back
        to JSON mode streaming. Streams:
        - TokenFrame: Individual token emissions during generation
        - DecisionFrame: Final decision with action (RESPOND, TOOL_CALL, or MOVE)

        The method intelligently parses:
        - Structured Decision responses
        - Tool/function calls from streaming deltas
        - Fallback JSON responses
        - Raw text responses

        Args:
            messages: Complete message list for decision context.
            schema: Optional response schema (Pydantic model or mapping).

        Yields:
            TokenFrame and DecisionFrame objects.

        Raises:
            RuntimeError: If OpenAI client not available and can't be created.

        Example:
            >>> messages = [Message(role="user", content="What next?")]
            >>> async for frame in provider.stream_decision(messages, schema=None):
            ...     print(f"Frame type: {frame.get('type')}")
        """
        # If a test client is provided that exposes a `chat.completions.create` streaming iterator,
        # use it; otherwise attempt to create a default OpenAI client lazily.
        client: AsyncOpenAI | None = self._client
        if client is None:
            try:
                from openai import AsyncOpenAI as AsyncOpenAIClient

                client = AsyncOpenAIClient()
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "OpenAI client not available; install 'openai' extra"
                ) from exc

        oai_messages = _to_openai_messages(messages)

        # Try structured outputs first (non-streaming)
        try:
            completion = await client.beta.chat.completions.parse(
                model=self._model,
                messages=oai_messages,
                response_format=Decision,
            )
            # For structured outputs, we get the parsed object directly
            decision = completion.choices[0].message.parsed
            if decision:
                # Convert Decision model to the expected dict format
                data = decision.model_dump()
                yield DecisionFrame(data=data).model_dump()
            return
        except (AttributeError, Exception):
            # Fallback to streaming JSON mode
            pass

        # Fallback for streaming JSON mode (legacy behavior)
        # Aggregate the full text to yield a final decision
        full_text: List[str] = []
        tool_calls: Dict[int, Dict[str, Any]] = {}

        # Start streaming chat completion with JSON mode
        try:
            stream = await client.chat.completions.create(
                model=self._model,
                messages=oai_messages,
                stream=True,
                response_format={"type": "json_object"},
            )
        except TypeError:
            # Fake clients in tests may not accept response_format
            result = client.chat.completions.create(
                model=self._model, messages=oai_messages, stream=True
            )
            # Wrap sync iterator for use in async for
            stream = _async_iter_wrapper(result)

        # Iterate through the stream (async or wrapped sync)
        async for chunk in stream:
            try:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta is None and isinstance(choice, dict):
                    delta = choice.get("delta")
            except Exception:  # pragma: no cover - tolerate shape variance
                delta = None

            # Handle streaming content tokens
            content = None
            if delta is not None:
                content = getattr(delta, "content", None)
                if content is None and isinstance(delta, dict):
                    content = delta.get("content")
            if content:
                full_text.append(content)
                yield TokenFrame(
                    data={"role": "assistant", "delta": content}
                ).model_dump()

            # Handle function/tool-calling deltas
            tool_delta = None
            if delta is not None:
                tool_delta = getattr(delta, "tool_calls", None)
                if tool_delta is None and isinstance(delta, dict):
                    tool_delta = delta.get("tool_calls")
            if tool_delta:
                for item in tool_delta:
                    try:
                        idx = getattr(item, "index", None)
                    except Exception:
                        idx = item.get("index") if isinstance(item, dict) else None
                    try:
                        func = getattr(item, "function", None)
                        if func is None and isinstance(item, dict):
                            func = item.get("function")
                        name = getattr(func, "name", None) if func is not None else None
                        if name is None and isinstance(func, dict):
                            name = func.get("name")
                        args_delta = (
                            getattr(func, "arguments", None)
                            if func is not None
                            else None
                        )
                        if args_delta is None and isinstance(func, dict):
                            args_delta = func.get("arguments")
                    except Exception:  # pragma: no cover
                        name = None
                        args_delta = None
                    if idx is None:
                        idx = 0
                    entry = tool_calls.setdefault(
                        int(idx), {"name": name or "", "arguments": ""}
                    )
                    if name:
                        entry["name"] = name
                    if args_delta:
                        entry["arguments"] = entry.get("arguments", "") + str(
                            args_delta
                        )

        # final decision: prefer tool_call if present, else try to parse JSON decision, else respond text
        if tool_calls:
            first = tool_calls[sorted(tool_calls.keys())[0]]
            tool_name = first.get("name") or ""
            raw_args = first.get("arguments") or ""
            try:
                tool_kwargs = json.loads(raw_args) if raw_args else {}
            except Exception:
                tool_kwargs = {"__raw__": raw_args}
            tool_data: Dict[str, Any] = {
                "action": "TOOL_CALL",
                "tool_call": {"tool_name": tool_name, "tool_kwargs": tool_kwargs},
            }
            # If schema is a mapping of tool_name -> Pydantic model, parse kwargs
            if isinstance(schema, dict) and tool_name in schema:
                model = schema[tool_name]
                try:
                    if isinstance(model, type) and issubclass(model, BaseModel):
                        parsed = model.model_validate(tool_kwargs)
                        tool_data["tool_call"]["tool_kwargs_parsed"] = (
                            parsed.model_dump()
                        )
                except Exception as exc:  # pragma: no cover
                    tool_data.setdefault("schema_error", str(exc))
            yield DecisionFrame(data=tool_data).model_dump()
        else:
            response_text = "".join(full_text)
            # First try to parse as structured Decision JSON
            try:
                obj = json.loads(response_text)
                # Validate against Decision schema
                decision = Decision.model_validate(obj)
                yield DecisionFrame(data=decision.model_dump()).model_dump()
                return
            except Exception:
                pass
            # Fallback: RESPOND action with raw text (optionally attempt schema parse)
            data = {"action": "RESPOND", "response": response_text}
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    obj = json.loads(response_text)
                    parsed = schema.model_validate(obj)
                    data["parsed"] = parsed.model_dump()
                except Exception:  # pragma: no cover - ignore parse errors
                    pass
            yield DecisionFrame(data=data).model_dump()

    async def stream_generate(
        self, messages: List[Union[Message, Dict[str, Any]]]
    ) -> AsyncIterator[ProviderFrame]:
        """Stream text generation without decision logic.

        Used for pure text generation (e.g., final responses, generation tasks).
        Yields only TokenFrame objects (no DecisionFrame).

        Args:
            messages: Message list for generation context.

        Yields:
            TokenFrame objects for streaming text output.

        Example:
            >>> msgs = [Message(role="user", content="Write a poem")]
            >>> async for frame in provider.stream_generate(msgs):
            ...     if frame["type"] == "io.token":
            ...         print(frame["data"]["delta"], end="")
        """
        # Implement in terms of stream_decision and pass through token events only
        async for frame in self.stream_decision(messages, schema=None):
            if frame.get("type") == EventType.TOKEN_EMITTED:
                yield frame


__all__ = ["OpenAI"]
