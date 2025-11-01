"""OpenAI provider adapter implementing LLMProviderPort (skeleton).

This adapter converts Nomos messages (with content parts) to OpenAI chat messages,
streams token deltas, and yields a final decision.completed with aggregated text.

Note: Function/tool-calling is out of scope for this initial adapter.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Optional

from nomos.core.events import EventType
from nomos.core.ports import LLMProviderPort


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
    oai: List[Dict[str, Any]] = []
    for m in messages:
        role = m.get("role")
        content = m.get("content")
        if isinstance(content, list):
            oai.append({"role": role, "content": _to_openai_content(content)})
        else:
            oai.append({"role": role, "content": content})
    return oai


class OpenAIProvider(LLMProviderPort):
    def __init__(self, *, model: str = "gpt-4o-mini", client: Optional[Any] = None) -> None:  # noqa: ANN401
        self._model = model
        self._client = client

    async def stream_decision(self, messages: List[Dict[str, Any]], schema: Any) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # If a test client is provided that exposes a `chat.completions.create` streaming iterator,
        # use it; otherwise attempt to create a default OpenAI client lazily.
        client = self._client
        if client is None:
            try:
                from openai import OpenAI  # type: ignore

                client = OpenAI()
            except Exception as exc:  # pragma: no cover - optional dependency
                raise RuntimeError("OpenAI client not available; install 'openai' extra") from exc

        oai_messages = _to_openai_messages(messages)
        # Start streaming chat completion
        stream = client.chat.completions.create(model=self._model, messages=oai_messages, stream=True)
        # Aggregate the full text to yield a final decision
        full_text: List[str] = []
        # The iterator is synchronous; bridge into async context
        for chunk in stream:
            try:
                choice = chunk.choices[0]
                delta = getattr(choice, "delta", None)
                if delta is None:
                    delta = choice.get("delta")  # type: ignore[attr-defined]
                content = getattr(delta, "content", None) if delta is not None else None
                if content is None and isinstance(delta, dict):
                    content = delta.get("content")
            except Exception:  # pragma: no cover - tolerate shape variance
                content = None
            if content:
                full_text.append(content)
                yield {"type": EventType.TOKEN_EMITTED.value, "data": {"role": "assistant", "delta": content}}

        # final decision
        response_text = "".join(full_text)
        yield {
            "type": EventType.DECISION_COMPLETED.value,
            "data": {"action": "RESPOND", "response": response_text},
        }

    async def stream_generate(self, messages: List[Dict[str, Any]]) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        # Implement in terms of stream_decision and pass through token events only
        async for frame in self.stream_decision(messages, schema=None):  # type: ignore[arg-type]
            if frame.get("type") == EventType.TOKEN_EMITTED.value:
                yield frame


__all__ = ["OpenAIProvider"]

