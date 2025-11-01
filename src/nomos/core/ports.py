"""Hexagonal ports (interfaces) — skeleton.

Define the primary interfaces that the domain/application depend upon.
Adapters will implement these in provider/tool/store/server packages.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Protocol, Union
from .types import ProviderSchema, ProviderFrame, ToolFrameType, ToolArgs, ToolContext
from .schemas import Message, Checkpoint
from .events import SessionEvent


class LLMProviderPort(Protocol):
    async def stream_decision(
        self, messages: List[Union[Message, Dict[str, Any]]], schema: ProviderSchema
    ) -> AsyncIterator[ProviderFrame]: ...

    async def stream_generate(
        self, messages: List[Union[Message, Dict[str, Any]]]
    ) -> AsyncIterator[ProviderFrame]: ...


class ToolRunnerPort(Protocol):
    async def run(
        self, tool_name: str, args: ToolArgs, ctx: ToolContext
    ) -> AsyncIterator[ToolFrameType]: ...


class EventStorePort(Protocol):
    async def append(self, session_id: str, events: List[SessionEvent]) -> None: ...

    async def read_by_session(self, session_id: str) -> List[SessionEvent]: ...

    def subscribe(self, session_id: str) -> AsyncIterator[SessionEvent]: ...


class CheckpointStorePort(Protocol):
    async def save(self, session_id: str, checkpoint: Checkpoint) -> None: ...

    async def load(self, session_id: str, checkpoint_id: str) -> Checkpoint: ...


__all__ = [
    "LLMProviderPort",
    "ToolRunnerPort",
    "EventStorePort",
    "CheckpointStorePort",
]
