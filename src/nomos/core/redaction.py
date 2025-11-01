"""Redaction utilities for event payloads.

Provides a simple deep redaction helper with a default set of sensitive keys.
Redaction is opt-in and applied by the orchestrator when configured.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping, MutableMapping


DEFAULT_SENSITIVE_KEYS = {"api_key", "apikey", "token", "access_token", "secret", "password"}


def redact_mapping(
    obj: Mapping[str, Any], *, sensitive_keys: Iterable[str] | None = None, mask: str = "***"
) -> Dict[str, Any]:
    """Return a redacted copy of the mapping, masking sensitive keys recursively.

    - Handles nested dicts and lists.
    - Leaves non-dict/list values as-is.
    """
    keys = set((sensitive_keys or DEFAULT_SENSITIVE_KEYS))

    def _redact(value: Any) -> Any:  # noqa: ANN401
        if isinstance(value, Mapping):
            return {k: (mask if k.lower() in keys else _redact(v)) for k, v in value.items()}
        if isinstance(value, list):
            return [_redact(v) for v in value]
        return value

    return _redact(dict(obj))


__all__ = ["redact_mapping", "DEFAULT_SENSITIVE_KEYS"]

