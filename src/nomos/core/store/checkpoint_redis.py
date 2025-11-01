"""Redis checkpoint store (optional, requires 'redis' extra).

This adapter is provided as an optional implementation for Spike 6.
Not used in CI; import will fail unless redis client is available.
"""

from __future__ import annotations

import json
from typing import Any, Dict


class RedisCheckpointStore:
    def __init__(
        self, *, url: str = "redis://localhost/0", prefix: str = "nomos:cp:"
    ) -> None:
        try:
            import redis.asyncio as redis  # type: ignore
        except Exception as exc:  # pragma: no cover - optional
            raise RuntimeError("redis extra not installed") from exc
        self._r = redis.from_url(url)
        self._prefix = prefix

    def _key(self, session_id: str, checkpoint_id: str) -> str:
        return f"{self._prefix}{session_id}:{checkpoint_id}"

    async def save(self, session_id: str, checkpoint: Dict[str, Any]) -> None:
        key = self._key(session_id, str(checkpoint.get("id") or "default"))
        await self._r.set(key, json.dumps(checkpoint))

    async def load(self, session_id: str, checkpoint_id: str) -> Dict[str, Any]:
        key = self._key(session_id, checkpoint_id)
        raw = await self._r.get(key)
        if not raw:
            raise KeyError(f"checkpoint not found: {checkpoint_id}")
        return json.loads(raw)


__all__ = ["RedisCheckpointStore"]
