"""In-memory checkpoint store implementation (for development and testing).

This module provides a simple in-memory implementation of the CheckpointStore protocol.
Checkpoints are stored in process memory and lost on restart. Suitable for:
- Development and prototyping
- Testing and unit tests
- Single-process deployments

For production use, implement CheckpointStore with durable storage (PostgreSQL, Redis, etc).
"""

from __future__ import annotations

from typing import Dict, Tuple

from nomos.core.schemas import Checkpoint
from nomos.core.interfaces import CheckpointStore


class InMemoryCheckpointStore(CheckpointStore):
    """In-memory checkpoint store.

    Stores checkpoints indexed by (session_id, checkpoint_id) tuple.
    Provides simple save/load semantics without durability.

    Example:
        >>> store = InMemoryCheckpointStore()
        >>> cp = Checkpoint(id="cp1", node_id="gather", data={"info": "value"})
        >>> await store.save("session1", cp)
        >>> loaded = await store.load("session1", "cp1")
        >>> loaded.node_id
        "gather"
    """

    def __init__(self) -> None:
        """Initialize the checkpoint store.

        Sets up empty storage mapping (session_id, checkpoint_id) tuples
        to Checkpoint objects.
        """
        self._store: Dict[Tuple[str, str], Checkpoint] = {}

    async def save(self, session_id: str, checkpoint: Checkpoint) -> None:
        """Save a checkpoint for a session.

        Stores the checkpoint at key (session_id, checkpoint.id).
        Overwrites any existing checkpoint with the same ID for the session.

        Args:
            session_id: Session identifier.
            checkpoint: Checkpoint object with id, node_id, and data.
        """
        cid = checkpoint.id or "default"
        self._store[(session_id, cid)] = checkpoint

    async def load(self, session_id: str, checkpoint_id: str) -> Checkpoint:
        """Load a checkpoint for a session.

        Args:
            session_id: Session identifier.
            checkpoint_id: Checkpoint identifier.

        Returns:
            The Checkpoint object.

        Raises:
            KeyError: If checkpoint does not exist for this session.
        """
        key = (session_id, checkpoint_id)
        if key not in self._store:
            raise KeyError(f"checkpoint not found: {checkpoint_id}")
        return self._store[key]


__all__ = ["InMemoryCheckpointStore"]
