"""OpenAI provider adapter implementing LLMProviderPort (skeleton).

This adapter converts Nomos messages (with content parts) to OpenAI chat messages,
streams token deltas, and yields a final decision.completed with aggregated text.

Note: Function/tool-calling is out of scope for this initial adapter.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional
import json

from nomos.core.events import EventType, TokenFrame, DecisionFrame
from nomos.core.schemas import Message
from pydantic import BaseModel
from nomos.core.ports import LLMProviderPort
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


def _to_openai_messages(messages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:  # noqa: ANN401
    # Normalize to typed Message for validation, then build provider payloads
    oai: List[Dict[str, Any]] = []
    for m in messages:
        try:
            typed = Message.model_validate(m)
            role = typed.role
            content = typed.content
        except Exception:
            # best-effort fallback for raw dicts
            role = m.get("role")
            content = m.get("content")
        if isinstance(content, list):
            raw_parts = [
                c.model_dump() if hasattr(c, "model_dump") else c for c in content
            ]
            oai.append({"role": role, "content": _to_openai_content(raw_parts)})
        else:
            oai.append({"role": role, "content": content})
    return oai


class OpenAIProvider(LLMProviderPort):
    def __init__(
        self, *, model: str = "gpt-4o-mini", client: Optional[Any] = None
    ) -> None:  # noqa: ANN401
        self._model = model
        self._client = client

    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: ProviderSchema
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
        # Start streaming chat completion
        stream = client.chat.completions.create(
            model=self._model, messages=oai_messages, stream=True
        )
        # Aggregate the full text to yield a final RESPOND decision, or collect tool_call deltas
        full_text: List[str] = []
        tool_calls: Dict[int, Dict[str, Any]] = {}
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

        # final decision: prefer tool_call if present, else respond text
        if tool_calls:
            first = tool_calls[sorted(tool_calls.keys())[0]]
            tool_name = first.get("name") or ""
            raw_args = first.get("arguments") or ""
            try:
                tool_kwargs = json.loads(raw_args) if raw_args else {}
            except Exception:
                tool_kwargs = {"__raw__": raw_args}
            data: Dict[str, Any] = {
                "action": "TOOL_CALL",
                "tool_call": {"tool_name": tool_name, "tool_kwargs": tool_kwargs},
            }
            # If schema is a mapping of tool_name -> Pydantic model, parse kwargs
            if isinstance(schema, dict) and tool_name in schema:
                model = schema[tool_name]
                try:
                    if isinstance(model, type) and issubclass(model, BaseModel):
                        parsed = model.model_validate(tool_kwargs)
                        data["tool_call"]["tool_kwargs_parsed"] = parsed.model_dump()
                except Exception as exc:  # pragma: no cover
                    data.setdefault("schema_error", str(exc))
            yield DecisionFrame(data=data).model_dump()
        else:
            response_text = "".join(full_text)
            data = {"action": "RESPOND", "response": response_text}
            # If schema is a Pydantic model class, try to parse JSON body
            if isinstance(schema, type) and issubclass(schema, BaseModel):
                try:
                    obj = json.loads(response_text)
                    parsed = schema.model_validate(obj)
                    data["parsed"] = parsed.model_dump()
                except Exception:  # pragma: no cover - ignore parse errors
                    pass
            yield DecisionFrame(data=data).model_dump()

    async def stream_generate(
        self, messages: List[Dict[str, Any]]
    ) -> AsyncIterator[ProviderFrame]:
        # Implement in terms of stream_decision and pass through token events only
        async for frame in self.stream_decision(messages, schema=None):  # type: ignore[arg-type]
            if frame.get("type") == EventType.TOKEN_EMITTED.value:
                yield frame


__all__ = ["OpenAIProvider"]
