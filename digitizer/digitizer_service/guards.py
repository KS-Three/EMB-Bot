"""The service's outer guards: what a request may cost before any route runs.

Two pure-ASGI middlewares, kept out of `app.py` so each can be pinned against a
throwaway app in a test without touching the shared job registry.

  - `BodyLimit` refuses a body over its route's byte budget with a 413 BEFORE
    it is buffered: a declared `Content-Length` is checked up front, and a
    chunked body (no length) is counted as it streams and cut off at the
    budget. The routes' own `len(data) > MAX_UPLOAD_BYTES` checks still run —
    this is the layer that stops a 2 GB POST from being spooled to disk first.
  - `Deadline` answers 504 when a request has not produced a response in
    `seconds`. It does NOT wait for the handler to notice: a handler parked in
    `run_in_threadpool` cannot be cancelled until its thread returns, and
    `asyncio.wait_for` would wait for exactly that. The handler's task is
    cancelled and left to finish on its own; anything it sends afterwards is
    dropped. A digitize JOB is not a request — it is bounded separately by
    `JobRegistry`'s timeout, because the request that started it returned 202
    long ago.

Every refusal is JSON `{"detail": ...}`, the same shape an `HTTPException`
produces, because the Studio shows `detail` verbatim.
"""
from __future__ import annotations

import asyncio
import json
import math
from typing import Callable

from starlette.exceptions import HTTPException


def _mb(n: int) -> str:
    """One decimal, rounded UP, so a file 1 byte over a 12 MB limit reads
    '12.1 MB' and never 'Artwork is 12 MB; the limit is 12 MB'."""
    return f"{math.ceil(n * 10 / 1024 / 1024) / 10:.1f}".removesuffix(".0") + " MB"


def too_large_detail(size: int | None, limit: int) -> str:
    said = f"Upload is {_mb(size)}; the limit" if size is not None else "Upload is over the limit; it"
    return f"{said} is {_mb(limit)}. Export it smaller and try again."


async def _send_json(send, status: int, detail: str, headers: dict | None = None) -> None:
    body = json.dumps({"detail": detail}).encode()
    raw = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    raw += [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    await send({"type": "http.response.start", "status": status, "headers": raw})
    await send({"type": "http.response.body", "body": body})


class BodyLimit:
    """413 for a body over its budget, declared or streamed. `limit_for(path)`
    -> (budget, advertised): the bytes allowed through, and the limit the
    message names — an upload route lets its framing through on top of the
    file limit, but the customer should only ever hear the file limit."""

    def __init__(self, app, limit_for: Callable[[str], tuple[int, int]]):
        self.app = app
        self.limit_for = limit_for

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        limit, advertised = self.limit_for(scope.get("path", ""))
        declared = dict(scope.get("headers") or ()).get(b"content-length")
        if declared is not None:
            if not declared.isdigit():
                return await _send_json(send, 400, "Content-Length is not a number.")
            if int(declared) > limit:
                return await _send_json(send, 413, too_large_detail(int(declared), advertised))

        seen = 0

        async def counted():
            nonlocal seen
            msg = await receive()
            if msg["type"] == "http.request":
                seen += len(msg.get("body", b""))
                if seen > limit:
                    # An HTTPException, not a private type: FastAPI re-raises
                    # HTTPException from body parsing but turns anything else
                    # into a bland 400 "error parsing the body".
                    raise HTTPException(413, too_large_detail(None, advertised))
            return msg

        await self.app(scope, counted, send)


class Deadline:
    """504 when no response has started within `seconds()`."""

    def __init__(self, app, seconds: Callable[[], float]):
        self.app = app
        self.seconds = seconds

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        started = False
        abandoned = False

        async def guarded_send(msg):
            nonlocal started
            if abandoned:
                return
            if msg["type"] == "http.response.start":
                started = True
            await send(msg)

        task = asyncio.ensure_future(self.app(scope, receive, guarded_send))
        done, _ = await asyncio.wait({task}, timeout=self.seconds())
        if task in done:
            return task.result()
        if started:
            # Mid-body: too late for a status code; let it finish.
            return await task
        abandoned = True
        task.cancel()
        # Retrieve its eventual exception so asyncio does not log it as lost.
        task.add_done_callback(lambda t: t.cancelled() or t.exception())
        await _send_json(
            send, 504,
            "That took too long and was stopped. Try a smaller or simpler "
            "image; if it keeps happening, try again in a minute.",
        )
