"""In-memory checkpoint store (dev/local) — skeleton."""

from __future__ import annotations

from typing import Dict, Tuple

from nomos.core.schemas import Checkpoint
from nomos.core.interfaces import CheckpointStore


class InMemoryCheckpointStore(CheckpointStore):
    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], Checkpoint] = {}

    async def save(self, session_id: str, checkpoint: Checkpoint) -> None:
        cid = checkpoint.id or "default"
        self._store[(session_id, cid)] = checkpoint

    async def load(self, session_id: str, checkpoint_id: str) -> Checkpoint:
        key = (session_id, checkpoint_id)
        if key not in self._store:
            raise KeyError(f"checkpoint not found: {checkpoint_id}")
        return self._store[key]


__all__ = ["InMemoryCheckpointStore"]
