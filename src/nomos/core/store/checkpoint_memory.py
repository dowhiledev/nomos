"""In-memory checkpoint store (dev/local) — skeleton."""

from __future__ import annotations

from typing import Any, Dict, Tuple


class InMemoryCheckpointStore:
    def __init__(self) -> None:
        self._store: Dict[Tuple[str, str], Dict[str, Any]] = {}

    async def save(self, session_id: str, checkpoint: Dict[str, Any]) -> None:
        cid = checkpoint.get("id") or "default"
        self._store[(session_id, cid)] = checkpoint

    async def load(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        key = (session_id, checkpoint_id)
        if key not in self._store:
            raise KeyError(f"checkpoint not found: {checkpoint_id}")
        return self._store[key]


__all__ = ["InMemoryCheckpointStore"]
