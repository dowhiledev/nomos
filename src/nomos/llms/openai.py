"""OpenAI provider adapter implementing LLMProvider (skeleton).

This adapter converts Nomos messages (with content parts) to OpenAI chat messages,
streams token deltas, and yields a final decision.completed with aggregated text.

Note: Function/tool-calling is out of scope for this initial adapter.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional, Union
import json

from nomos.core.events import EventType, TokenFrame, DecisionFrame
from nomos.core.schemas import Message, Decision
from pydantic import BaseModel
from nomos.core.interfaces import LLMProvider
from nomos.core.types import ProviderSchema, ProviderFrame


def _to_openai_content(parts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:  # noqa: ANN401
    """Convert Nomos content parts to OpenAI message content array."""
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
    def __init__(
        self, *, model: str = "gpt-4o-mini", client: Optional[Any] = None
    ) -> None:  # noqa: ANN401
        self._model = model
        self._client = client

    def build_decision_messages(
        self,
        agent_spec,  # AgentSpec
        current_node_id: str,
        allowed_tools: List[str],
        base_messages: List[Union[Message, Dict[str, Any]]],
    ) -> List[Union[Message, Dict[str, Any]]]:
        """Build messages for decision making with system and assistant context."""
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

        # Build tools description (basic for now, since we don't have tool objects)
        tools_desc = []
        for tool_name in allowed_tools:
            tools_desc.append(f"- {tool_name}")
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
        # If a test client is provided that exposes a `chat.completions.create` streaming iterator,
        # use it; otherwise attempt to create a default OpenAI client lazily.
        client = self._client
        if client is None:
            try:
                from openai import OpenAI  # type: ignore

                client = OpenAI()
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError(
                    "OpenAI client not available; install 'openai' extra"
                ) from exc

        oai_messages = _to_openai_messages(messages)

        # Try structured outputs first (non-streaming)
        try:
            completion = client.beta.chat.completions.parse(
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
            stream = client.chat.completions.create(
                model=self._model,
                messages=oai_messages,
                stream=True,
                response_format={"type": "json_object"},
            )
        except TypeError:
            # Fake clients in tests may not accept response_format
            stream = client.chat.completions.create(
                model=self._model, messages=oai_messages, stream=True
            )

        # The iterator is synchronous; bridge into async context
        for chunk in stream:
            try:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta is None:
                    delta = choice.get("delta")  # type: ignore[attr-defined]
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
        # Implement in terms of stream_decision and pass through token events only
        async for frame in self.stream_decision(messages, schema=None):  # type: ignore[arg-type]
            if frame.get("type") == EventType.TOKEN_EMITTED.value:
                yield frame


__all__ = ["OpenAI"]
