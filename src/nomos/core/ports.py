"""Hexagonal ports (interfaces) — skeleton.

Define the primary interfaces that the domain/application depend upon.
Adapters will implement these in provider/tool/store/server packages.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Protocol


class LLMProviderPort(Protocol):
    async def stream_decision(
        self, messages: List[Dict[str, Any]], schema: Any
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        ...

    async def stream_generate(
        self, messages: List[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        ...


class ToolRunnerPort(Protocol):
    async def run(
        self, tool_name: str, args: Dict[str, Any], ctx: Dict[str, Any]
    ) -> AsyncIterator[Dict[str, Any]]:  # noqa: ANN401
        ...


class EventStorePort(Protocol):
    async def append(self, session_id: str, events: List[Dict[str, Any]]) -> None: ...

    async def read_by_session(self, session_id: str) -> List[Dict[str, Any]]: ...

    def subscribe(self, session_id: str) -> AsyncIterator[Dict[str, Any]]: ...


class CheckpointStorePort(Protocol):
    async def save(self, session_id: str, checkpoint: Dict[str, Any]) -> None: ...

    async def load(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]: ...


__all__ = [
    "LLMProviderPort",
    "ToolRunnerPort",
    "EventStorePort",
    "CheckpointStorePort",
]
