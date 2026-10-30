"""Cooperative cancellation for one digitize: a deadline the pipeline reads
at its stage seams and once per shape in stage 7.

**Why.** The service (`digitizer_service.jobs`) runs one job at a time and
reports a job RUNNING past `JOB_TIMEOUT_S` as failed -- but Python cannot
stop a thread, so until 2026-10-30 the abandoned job kept the single worker
and the NEXT upload queued behind work whose answer nobody would read. The
photo-style census (`docs/photo-style-census-2026-10-27.md`, item 6) measured
rows of 350-800 s on a loaded laptop; the Studio told the customer the first
job had stopped and then sat on their second for the rest of the first.

**What.** `scope(seconds)` arms a deadline for the current thread (a
`contextvars.ContextVar`, like `fill_section_travel`'s switch: the service's
worker thread arms it around `work()`; a library caller never does and pays
one `None` read per check). `check(stage)` raises `Abandoned` once the
deadline has passed. The pipeline calls `check` between stages 0, 1, 1.5, 2,
3 and 4 in `build_generation`, at the top of `finish_generation` and
`plan_stitches`, after stage 5, before every shape stage 7 sews, and at the
top of `run_preflight`. A check costs a clock read; it moves no number, so a
job that finishes in time is byte-identical with or without a scope
(`tests/test_service.py` pins the design's md5 both ways).

**What it cannot interrupt.** One call that runs past the whole budget on its
own: stage 2's region former (`photo_segment` / `quantize`; stained_glass
read 130 s there before PR #1192's bincount fix), the rembg / SAM2
subprocesses (which carry their own `*_timeout_s`), and stage 7's chaining
passes after emission. Those end, and the next check fires; the worker is
freed within one such call, not instantly.
"""
from __future__ import annotations

import contextvars
import time
from contextlib import contextmanager
from typing import Iterator

_DEADLINE: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "digitizer_deadline", default=None)


class Abandoned(Exception):
    """`check` found the deadline passed. `stage` names the seam that noticed;
    `over_s` is how far past the deadline the clock read there."""

    def __init__(self, stage: str, over_s: float):
        self.stage = stage
        self.over_s = over_s
        super().__init__(f"abandoned at {stage}, {over_s:.1f}s past the deadline")


@contextmanager
def scope(seconds: float | None) -> Iterator[None]:
    """Arm a deadline `seconds` from now for everything run inside. `None`
    arms nothing (the library default). Scopes nest: the inner one wins for
    its body and the outer is restored after."""
    if seconds is None:
        yield
        return
    token = _DEADLINE.set(time.monotonic() + float(seconds))
    try:
        yield
    finally:
        _DEADLINE.reset(token)


def check(stage: str) -> None:
    """Raise `Abandoned` if the armed deadline has passed; a no-op otherwise
    and when no scope is armed."""
    deadline = _DEADLINE.get()
    if deadline is not None:
        now = time.monotonic()
        if now > deadline:
            raise Abandoned(stage, now - deadline)


def remaining() -> float | None:
    """Seconds left on the armed deadline (negative once passed); None when
    no scope is armed."""
    deadline = _DEADLINE.get()
    return None if deadline is None else deadline - time.monotonic()
