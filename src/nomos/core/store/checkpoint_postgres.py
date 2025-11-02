"""Postgres checkpoint store (optional, requires 'asyncpg' extra).

This adapter is provided as an optional implementation for Spike 6.
Not used in CI; requires a table with schema: (session_id text, checkpoint_id text, payload jsonb, primary key(session_id, checkpoint_id)).
"""

from __future__ import annotations


from nomos.core.schemas import Checkpoint
from nomos.core.interfaces import CheckpointStore


class PostgresCheckpointStore(CheckpointStore):
    def __init__(self, dsn: str) -> None:
        try:
            from importlib import import_module

            import_module("asyncpg")
        except Exception as exc:  # pragma: no cover - optional
            raise RuntimeError("asyncpg extra not installed") from exc
        self._dsn = dsn

    async def _conn(self):  # type: ignore[no-untyped-def]
        import asyncpg  # type: ignore

        return await asyncpg.connect(self._dsn)

    async def save(self, session_id: str, checkpoint: Checkpoint) -> None:
        cp_id = str(checkpoint.id or "default")
        async with await self._conn() as conn:  # type: ignore[attr-defined]
            await conn.execute(
                """
                INSERT INTO nomos_checkpoints (session_id, checkpoint_id, payload)
                VALUES ($1, $2, $3)
                ON CONFLICT (session_id, checkpoint_id) DO UPDATE SET payload = EXCLUDED.payload
                """,
                session_id,
                cp_id,
                checkpoint.model_dump(),
            )

    async def load(self, session_id: str, checkpoint_id: str) -> Checkpoint:
        async with await self._conn() as conn:  # type: ignore[attr-defined]
            row = await conn.fetchrow(
                "SELECT payload FROM nomos_checkpoints WHERE session_id=$1 AND checkpoint_id=$2",
                session_id,
                checkpoint_id,
            )
        if not row:
            raise KeyError(f"checkpoint not found: {checkpoint_id}")
        return Checkpoint.model_validate(dict(row[0]))  # type: ignore[index]


__all__ = ["PostgresCheckpointStore"]
