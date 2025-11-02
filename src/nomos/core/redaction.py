"""Redaction utilities for sensitive data in events and logs.

This module provides helpers for redacting sensitive information from event payloads,
logs, and stored data. Redaction is opt-in and applied by the orchestrator when
configured, protecting secrets while preserving event auditability.

Supports:
- Recursive redaction of nested structures (dicts and lists)
- Customizable sensitive key lists
- Configurable masking strings (default "***")
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, Mapping


DEFAULT_SENSITIVE_KEYS = {
    "api_key",
    "apikey",
    "token",
    "access_token",
    "secret",
    "password",
}
"""Default set of keys considered sensitive.

These are commonly targeted attack vectors. Additional keys can be specified
per-call via the sensitive_keys parameter.
"""


def redact_mapping(
    obj: Mapping[str, Any],
    *,
    sensitive_keys: Iterable[str] | None = None,
    mask: str = "***",
) -> Dict[str, Any]:
    """Return a redacted copy of a mapping with sensitive values masked.
    
    Recursively traverses the mapping and replaces values for sensitive keys
    with the mask string. Preserves all other data unchanged. Works with nested
    dicts and lists.
    
    Args:
        obj: The input mapping (dict-like) to redact.
        sensitive_keys: Set of key names to redact. Defaults to DEFAULT_SENSITIVE_KEYS.
            Keys are case-insensitive.
        mask: String to use for masking sensitive values (default "***").
    
    Returns:
        A new dict with sensitive values masked. The input obj is not modified.
    
    Raises:
        None. Function is defensive and won't crash on unexpected types.
    
    Example:
        >>> data = {
        ...     "username": "alice",
        ...     "api_key": "secret123",
        ...     "nested": {"token": "xyz"}
        ... }
        >>> redacted = redact_mapping(data)
        >>> redacted["api_key"]
        "***"
        >>> redacted["nested"]["token"]
        "***"
        >>> redacted["username"]
        "alice"
    """
    keys = set((sensitive_keys or DEFAULT_SENSITIVE_KEYS))

    def _redact(value: Any) -> Any:  # noqa: ANN401
        if isinstance(value, Mapping):
            return {
                k: (mask if k.lower() in keys else _redact(v)) for k, v in value.items()
            }
        if isinstance(value, list):
            return [_redact(v) for v in value]
        return value

    return _redact(dict(obj))



__all__ = ["redact_mapping", "DEFAULT_SENSITIVE_KEYS"]
