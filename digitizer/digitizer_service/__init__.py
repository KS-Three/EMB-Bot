"""digitizer-service — the localhost HTTP face of digitizer-core (build step 8).

`app` is the FastAPI application; `python -m digitizer_service` runs it.
"""
from .app import app

__all__ = ["app"]
