"""Lightweight observability: counters + optional OTEL spans."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Dict

EVENT_COUNTERS: Dict[str, int] = {}


def inc(event_type: str) -> None:
    EVENT_COUNTERS[event_type] = EVENT_COUNTERS.get(event_type, 0) + 1


def reset_counters() -> None:
    EVENT_COUNTERS.clear()


def _otel_enabled() -> bool:
    return os.getenv("NOMOS_ENABLE_OTEL", "false").lower() == "true"


@contextmanager
def span(name: str):  # noqa: ANN001
    if not _otel_enabled():
        yield
        return
    try:
        from opentelemetry import trace  # type: ignore

        tracer = trace.get_tracer(__name__)
        with tracer.start_as_current_span(name):
            yield
    except Exception:  # pragma: no cover - optional
        # fail open if OTEL not correctly configured
        yield


__all__ = ["EVENT_COUNTERS", "inc", "reset_counters", "span"]

