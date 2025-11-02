"""Lightweight observability: counters, timers, and optional OpenTelemetry spans.

This module provides minimal observability facilities for Nomos applications:
- Event counters for tracking occurrence of key events
- Latency histograms for performance monitoring
- Optional OpenTelemetry integration for distributed tracing
- Metrics snapshots for programmatic access to metrics

All facilities are optional and fail-open (no crashes if OTEL misconfigured).
"""

from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Dict, List

# Global observability state
EVENT_COUNTERS: Dict[str, int] = {}
"""Module-level event counter dictionary.

Maps event type strings to occurrence counts. Updated by inc() calls.
"""

LATENCY_HIST: Dict[str, List[float]] = {}
"""Module-level latency histogram dictionary.

Maps operation names to lists of measured durations (in seconds).
Populated by measure() context manager.
"""


def inc(event_type: str) -> None:
    """Increment an event counter.
    
    Increments the counter for the given event type. Counters persist for the
    lifetime of the process or until reset_counters() is called.
    
    Args:
        event_type: Unique event identifier (e.g., "decision.completed", "tool.error").
    
    Example:
        >>> inc("orchestrator.session_created")
        >>> inc("orchestrator.session_created")
        >>> EVENT_COUNTERS["orchestrator.session_created"]
        2
    """
    EVENT_COUNTERS[event_type] = EVENT_COUNTERS.get(event_type, 0) + 1


def reset_counters() -> None:
    """Reset all event counters and latency histograms to empty state.
    
    Useful for test isolation or starting fresh metrics collection.
    
    Example:
        >>> inc("test.event")
        >>> reset_counters()
        >>> EVENT_COUNTERS
        {}
    """
    EVENT_COUNTERS.clear()
    LATENCY_HIST.clear()


def _otel_enabled() -> bool:
    """Check if OpenTelemetry tracing is enabled.
    
    Returns True if NOMOS_ENABLE_OTEL environment variable is set to "true".
    
    Returns:
        Boolean indicating if OTEL is enabled.
    """
    return os.getenv("NOMOS_ENABLE_OTEL", "false").lower() == "true"


@contextmanager
def span(name: str):  # noqa: ANN001
    """Create an optional OpenTelemetry span.
    
    If OTEL is enabled (NOMOS_ENABLE_OTEL=true), creates a span with the given name
    and yields control. Otherwise yields immediately without overhead.
    
    Fails gracefully if OpenTelemetry is misconfigured.
    
    Args:
        name: Span name for tracing/debugging.
    
    Yields:
        None (context manager pattern).
    
    Example:
        >>> with span("orchestrator.process_decision"):
        ...     # Decision processing happens here
        ...     pass
    """
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
    """Record a latency measurement.
    
    Adds a single latency measurement to the histogram for the given operation.
    
    Args:
        name: Operation identifier (e.g., "orchestrator.decision_latency").
        seconds: Measured duration in seconds.
    
    Example:
        >>> record_latency("tool.execution", 0.5)
    """
    LATENCY_HIST.setdefault(name, []).append(seconds)


@contextmanager
def measure(name: str):  # noqa: ANN001
    """Context manager for measuring operation duration.
    
    Measures elapsed time of a code block and records it via record_latency().
    
    Args:
        name: Operation identifier.
    
    Yields:
        None (context manager pattern).
    
    Example:
        >>> with measure("database.query"):
        ...     result = db.execute(query)
        >>> # Latency automatically recorded in LATENCY_HIST["database.query"]
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        record_latency(name, time.perf_counter() - start)


def metrics_snapshot() -> Dict[str, Dict[str, float]]:  # noqa: ANN401
    """Return a snapshot of current metrics.
    
    Computes summary statistics from accumulated metrics:
    - Event counters: Raw occurrence counts
    - Latency averages: Mean of recorded measurements per operation
    
    Returns:
        Dict with "counters" (event counts) and "latency_avg" (mean durations).
    
    Example:
        >>> inc("event1")
        >>> inc("event1")
        >>> record_latency("op1", 1.0)
        >>> record_latency("op1", 2.0)
        >>> metrics_snapshot()
        {
            'counters': {'event1': 2},
            'latency_avg': {'op1': 1.5}
        }
    """
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
