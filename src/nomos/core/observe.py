"""Lightweight observability: counters, timers, and optional OTEL spans."""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Dict, List

EVENT_COUNTERS: Dict[str, int] = {}
LATENCY_HIST: Dict[str, List[float]] = {}


def inc(event_type: str) -> None:
    EVENT_COUNTERS[event_type] = EVENT_COUNTERS.get(event_type, 0) + 1


def reset_counters() -> None:
    EVENT_COUNTERS.clear()
    LATENCY_HIST.clear()


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


def record_latency(name: str, seconds: float) -> None:
    LATENCY_HIST.setdefault(name, []).append(seconds)


@contextmanager
def measure(name: str):  # noqa: ANN001
    start = time.perf_counter()
    try:
        yield
    finally:
        record_latency(name, time.perf_counter() - start)


def metrics_snapshot() -> Dict[str, Dict[str, float]]:  # noqa: ANN401
    """Return a simple snapshot of counters and latency stats (avg only)."""
    avg = {k: (sum(v) / len(v) if v else 0.0) for k, v in LATENCY_HIST.items()}
    return {"counters": dict(EVENT_COUNTERS), "latency_avg": avg}


__all__ = [
    "EVENT_COUNTERS",
    "LATENCY_HIST",
    "inc",
    "reset_counters",
    "span",
    "measure",
    "record_latency",
    "metrics_snapshot",
]
