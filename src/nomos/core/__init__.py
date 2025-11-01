"""Nomos vNext core exports (skeleton).

This module exposes the primary application entrypoints used by examples:
- Orchestrator: session actor API (create_session, stream, input, control, materialize_state)

The implementation follows DDD + Hexagonal + ES/CQRS principles:
- Domain events are the source of truth (see events.py)
- Ports define infrastructure boundaries (see ports.py)
- An in-memory event store is provided for local/dev usage (see store/memory.py)
"""

from .orchestrator import Orchestrator

__all__ = ["Orchestrator"]
