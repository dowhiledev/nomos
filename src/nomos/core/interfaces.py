"""Hexagonal interfaces (protocols) — skeleton.

Define the primary interfaces that the domain/application depend upon.
Adapters will implement these in provider/tool/store/server packages.
"""

from __future__ import annotations

from typing import Any, AsyncIterator, Dict, List, Protocol, Union
from .types import ProviderSchema, ProviderFrame, ToolFrameUnion, ToolArgs
from .schemas import Message, Checkpoint
from .events import SessionEvent


class LLMProvider(Protocol):
    def build_decision_messages(
        self,
        current_node_id: str,
        edges_txt: str,
        tools_list: List[str],
        base_messages: List[Union[Message, Dict[str, Any]]],
    ) -> List[Union[Message, Dict[str, Any]]]: ...

    def stream_decision(
        self, messages: List[Union[Message, Dict[str, Any]]], schema: ProviderSchema
    ) -> AsyncIterator[ProviderFrame]: ...

    def stream_generate(
        self, messages: List[Union[Message, Dict[str, Any]]]
    ) -> AsyncIterator[ProviderFrame]: ...


class ToolRunner(Protocol):
    def run(
        self, tool_name: str, args: ToolArgs, ctx: Dict[str, Any]
    ) -> AsyncIterator[ToolFrameUnion]: ...


class EventStore(Protocol):
    async def append(self, session_id: str, events: List[SessionEvent]) -> None: ...

    async def read_by_session(self, session_id: str) -> List[SessionEvent]: ...

    def subscribe(self, session_id: str) -> AsyncIterator[SessionEvent]: ...


class CheckpointStore(Protocol):
    async def save(self, session_id: str, checkpoint: Checkpoint) -> None: ...

    async def load(self, session_id: str, checkpoint_id: str) -> Checkpoint: ...


__all__ = [
    "LLMProvider",
    "ToolRunner",
    "EventStore",
    "CheckpointStore",
]
