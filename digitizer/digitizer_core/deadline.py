"""Cooperative cancellation for one digitize: a deadline and a cancel flag the
pipeline reads at its stage seams and inside the loops that can run long.

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
deadline has passed. The pipeline calls `check` between its stages and inside
the loops that make one shape, one photo segmentation, one border or one
preflight. A check costs a clock read; it moves no number, so a job that
finishes in time is byte-identical with or without a scope
(`tests/test_service.py` pins the design's md5 both ways).

**Where the checks are.** `grep -n "deadline.check" digitizer_core` is the
list; it is not kept by hand here, because every hand-kept inventory of it went
stale within a PR. The rule: a loop that can run past about half a second
starts with `deadline.check("<what it is>")`, and `tests/test_cancel_signal.py`
fails by name when one of the long loops loses its check.

Seams and loops added after the first inner-loop pass are pinned in
`tests/test_cancel_seams_1113.py` (stage 4's text-cluster neck cut and
letterform-prior fit, the keyline's loops) and `tests/test_cancel_in_fill.py`.

**`Abandoned` is a `BaseException`** (2026-11-13), like `KeyboardInterrupt`: it
is a stop signal, not an error. The pipeline is full of fail-open handlers
(`except Exception: return None` around a geometry call that may fail), and one
sits under an `lru_cache` (`stage6_fill._slant_for`), where a swallowed cancel
became a cached `None` for the NEXT job. A `BaseException` passes through all
of them with no hand-placed `except Abandoned: raise` beside each. Anything
that catches `BaseException` or a bare `except:` must re-raise it. The one
place that handles it by name is `digitizer_service.jobs.JobRegistry`.

**What it cannot interrupt.** One call with no loop of ours around it: a
single numpy / cv2 / GEOS call. The longest of those timed (the follow-up to #1408, PR body,
`logo_whitebg.png` 80 mm and `drone_render.png` 60 mm): `_link_cover`'s GEOS
union, 7.8 s, reached only with `chain_links` (default off); on the default
path, the decode and first read before stage 0 (about 2.4 s) and stage 2's
thin-ink read between its checks (about 1 s). Those end, and the next check
fires; the worker is freed within one such call, not instantly. The rembg and
SAM2 subprocesses ARE interrupted (`run_subprocess` kills the child), so their
own `*_timeout_s` is only the cap on a job nobody cancels.

**A customer's cancel rides the same checks (2026-11-12).** `scope` also takes
a `cancel` flag (a `threading.Event` the service sets from another thread
when the customer presses Cancel), and `check` raises `Cancelled` -- an
`Abandoned`, so everything that already unwinds for a deadline unwinds for a
cancel -- at the first check after the flag is set. `stitch_shape` and
`border_runs` undo their per-shape state in a `finally`, so a cancel
mid-shape leaves nothing for the next job. Still no number moves: a job that
is not cancelled is byte-identical.
"""
from __future__ import annotations

import contextvars
import subprocess
import threading
import time
from contextlib import contextmanager
from typing import Iterator

_DEADLINE: contextvars.ContextVar[float | None] = contextvars.ContextVar(
    "digitizer_deadline", default=None)
_CANCEL: contextvars.ContextVar[threading.Event | None] = contextvars.ContextVar(
    "digitizer_cancel", default=None)


class Abandoned(BaseException):
    """`check` found the deadline passed. `stage` names the seam that noticed;
    `over_s` is how far past the deadline the clock read there.

    A `BaseException`, like `KeyboardInterrupt`: this is a stop signal, not an
    error, and the pipeline is full of fail-open `except Exception: return
    None` handlers (a geometry call that may fail, a cached best-effort
    helper) that would swallow it -- or, under an `lru_cache`, remember the
    swallowed answer for the next job. A `BaseException` passes through all of
    them. The one place that catches it by name is `digitizer_service.jobs`."""

    def __init__(self, stage: str, over_s: float):
        self.stage = stage
        self.over_s = over_s
        super().__init__(f"abandoned at {stage}, {over_s:.1f}s past the deadline")

    def __reduce__(self):
        return (type(self), (self.stage, self.over_s))


class Cancelled(Abandoned):
    """`check` found the scope's cancel flag set: someone asked for this job
    to stop. Nothing ran late, so `over_s` is 0."""

    def __init__(self, stage: str):
        BaseException.__init__(self, f"cancelled at {stage}")
        self.stage = stage
        self.over_s = 0.0

    def __reduce__(self):
        return (type(self), (self.stage,))


@contextmanager
def scope(seconds: float | None,
          cancel: threading.Event | None = None) -> Iterator[None]:
    """Arm a deadline `seconds` from now for everything run inside, and/or a
    `cancel` flag another thread may set. `None` arms nothing (the library
    default). Scopes nest: the inner one wins for its body and the outer is
    restored after."""
    tokens = []
    if seconds is not None:
        tokens.append((_DEADLINE, _DEADLINE.set(time.monotonic() + float(seconds))))
    if cancel is not None:
        tokens.append((_CANCEL, _CANCEL.set(cancel)))
    try:
        yield
    finally:
        for var, token in reversed(tokens):
            var.reset(token)


def check(stage: str) -> None:
    """Raise `Cancelled` if the armed cancel flag is set, `Abandoned` if the
    armed deadline has passed; a no-op otherwise and when no scope is armed."""
    cancel = _CANCEL.get()
    if cancel is not None and cancel.is_set():
        raise Cancelled(stage)
    deadline = _DEADLINE.get()
    if deadline is not None:
        now = time.monotonic()
        if now > deadline:
            raise Abandoned(stage, now - deadline)


def run_subprocess(args: list[str], *, timeout: float,
                   poll_s: float = 0.5) -> subprocess.CompletedProcess:
    """`subprocess.run(args, capture_output=True, text=True, timeout=timeout)`
    that also reads `check` every `poll_s` seconds while the child runs.

    A cancel or the job deadline kills the child, waits for it and re-raises
    `Abandoned`, so the rembg / SAM2 workers no longer hold the service's one
    worker for their whole run. Everything else is `subprocess.run`'s: the
    child is killed and `subprocess.TimeoutExpired` raised past `timeout`,
    `OSError` comes out of the launch, the return code is the caller's to read.
    With no scope armed (a library caller) it IS `subprocess.run`, call for call.
    """
    if _CANCEL.get() is None and _DEADLINE.get() is None:
        return subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    end =time.monotonic() + float(timeout)
    with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          text=True) as proc:
        try:
            while True:
                try:
                    out, err = proc.communicate(
                        timeout=max(0.0, min(poll_s, end - time.monotonic())))
                    break
                except subprocess.TimeoutExpired:
                    check("subprocess")
                    if time.monotonic() >= end:
                        raise
        except BaseException:           # Abandoned, the timeout, an interrupt
            proc.kill()
            proc.wait()
            raise
        return subprocess.CompletedProcess(args, proc.returncode, out, err)


def remaining() -> float | None:
    """Seconds left on the armed deadline (negative once passed); None when
    no scope is armed."""
    deadline = _DEADLINE.get()
    return None if deadline is None else deadline - time.monotonic()
