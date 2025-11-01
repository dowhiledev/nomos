"""Conceptual SSE/WS server for Nomos vNext example (user code).

Provides a transport layer on top of the library-first workflow.
Relies entirely on vNext server utilities; no local placeholders.
"""

from __future__ import annotations

from nomos.server import create_app  # provided by vNext

from .graph import make_agent


# Library-provided factory returns a FastAPI app with /v2 endpoints enabled
app = create_app(agent=make_agent())

__all__ = ["app"]
