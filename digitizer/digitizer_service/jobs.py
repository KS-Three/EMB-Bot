"""The job registry: one digitize at a time, results cached by content.

Digitizing is tens of seconds of CPU-bound numpy and OpenCV. Two of them at
once on a laptop makes both slower and finishes neither, so there is exactly
one worker and requests queue behind it.

**The cache is the point.** A review screen's loop is "change one parameter,
look again", and the expensive half of the pipeline (stages 1-4) only depends
on the artwork and the stage 1-4 parameters. Keying finished results by
sha256(image) + the config that produced them means resubmitting an unchanged
request is free, which is what makes that loop usable — and what build step 8's
blueprint amendment asked for.

Nothing here is durable. The service is a localhost accelerator, not a
database: Studio owns the project file, and a restart simply costs a re-run.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
import traceback

from .errors import customer_message, raw as raw_error
import uuid
from collections import OrderedDict
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

QUEUED = "queued"
RUNNING = "running"
DONE = "done"
ERROR = "error"

# A finished result is a few hundred KB of stitch records. Keeping the last 32
# covers any realistic review session; unbounded would be a slow leak in a
# process meant to run all day.
MAX_CACHED = 32

# A job running longer than this is reported as failed. Python cannot stop a
# thread, so the work itself runs on and its result is thrown away — this is
# what the customer sees, not a reclaimed CPU. A healthy job is tens of
# seconds; this is a runaway guard, not a performance budget.
JOB_TIMEOUT_S = 600.0

# Jobs submitted but not finished — queued, running, and timed-out work still
# holding the worker. Each one keeps its decoded raster (up to 2800^2 x 3
# bytes) and its upload alive in a closure, so an unbounded queue is an
# unbounded heap. Past this the submit is refused with 503 instead.
MAX_INFLIGHT = 4

TIMED_OUT = ("That design took too long to digitize and was stopped. Try a "
             "smaller or simpler image, or crop to just the logo.")

log = logging.getLogger("digitizer_service")


class Busy(Exception):
    """`JobRegistry.submit` refused: MAX_INFLIGHT jobs already in flight."""


def show_tracebacks() -> bool:
    """Tracebacks ride on a failed job's `detail` only on a tokenless
    (loopback, developer) service. Once `EMBBOT_SERVICE_TOKEN` is set the
    service is reachable by someone else, and a stack trace names files, line
    numbers and library versions — it goes to the log instead."""
    return not os.environ.get("EMBBOT_SERVICE_TOKEN")


@dataclass
class Job:
    id: str
    key: str
    state: str = QUEUED
    result: dict | None = None
    error: str | None = None
    detail: str | None = None
    started: float | None = None
    _future: Future | None = field(default=None, repr=False)

    def public(self) -> dict:
        out: dict[str, Any] = {"job_id": self.id, "state": self.state}
        if self.state == DONE and self.result is not None:
            out.update(self.result)
        if self.state == ERROR:
            out["error"] = self.error
            if self.detail:
                out["detail"] = self.detail
        return out


def content_key(image: bytes, config: dict) -> str:
    """Cache key: the artwork plus the parameters that shaped it.

    The config is canonicalized (sorted keys, compact separators) so two
    logically identical requests that serialize differently still hit.
    """
    h = hashlib.sha256()
    h.update(hashlib.sha256(image).digest())
    h.update(json.dumps(config, sort_keys=True, separators=(",", ":"), default=str).encode())
    return h.hexdigest()


# The shape-layers contract's review-edit keys — the four config fields that
# stages 0-4 never read (they are applied between stage 4 and the palette,
# see `pipeline.finish_generation`). Everything ELSE in the config is part of
# the generation's identity. Pinned by tests/test_generation_cache.py so a
# new edit key being added to the contract forces a decision here rather
# than silently invalidating every edit's cache hit.
EDIT_KEYS = frozenset(
    {"deleted_shape_ids", "shape_overrides", "merge_shape_ids", "split_shapes"}
)


def generation_key(image: bytes, config: dict) -> str:
    """Cache key for the stage 0-4 generation: `content_key` with the
    review-edit fields stripped, so every edit of one artwork under one
    parameter set lands on the same expensive prefix."""
    return content_key(image, {k: v for k, v in config.items() if k not in EDIT_KEYS})


# A generation holds the prepped raster plus vectorized regions — roughly
# 10-40 MB for a photo. Four covers the realistic editing pattern (the shape
# being edited, plus a couple of parameter variants being A/B'd) without
# letting an all-day service grow without bound.
MAX_GENERATIONS = 4


class GenerationCache:
    """LRU for `pipeline.Generation` objects, keyed by `generation_key`.

    Entries are stored pristine and must stay that way: every consumer takes
    `Generation.fork()` before finishing from one (the fork is what isolates
    `apply_shape_edits`' in-place mutation), so `get` hands back the shared
    original and trusts the caller's fork discipline —
    `digitizer_service.app`'s `/digitize` worker is the only caller.

    Thread-safety note: with `JobRegistry(workers=1)` all access happens on
    the single digitize worker thread; the lock is defense for a future
    worker-count bump, not a load-bearing requirement today.
    """

    def __init__(self, max_entries: int = MAX_GENERATIONS):
        self._lock = threading.Lock()
        self._max = max_entries
        self._entries: OrderedDict[str, Any] = OrderedDict()

    def get(self, key: str):
        with self._lock:
            gen = self._entries.get(key)
            if gen is not None:
                self._entries.move_to_end(key)
            return gen

    def put(self, key: str, gen) -> None:
        with self._lock:
            self._entries[key] = gen
            self._entries.move_to_end(key)
            while len(self._entries) > self._max:
                self._entries.popitem(last=False)

    def clear(self) -> None:
        with self._lock:
            self._entries.clear()

    def stats(self) -> dict:
        with self._lock:
            return {"entries": len(self._entries), "max": self._max}


class JobRegistry:
    def __init__(self, workers: int = 1, timeout_s: float = JOB_TIMEOUT_S,
                 max_inflight: int = MAX_INFLIGHT):
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._by_key: dict[str, str] = {}
        self.timeout_s = timeout_s
        self.max_inflight = max_inflight
        self._inflight = 0
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="digitize")

    def _cached_locked(self, key: str) -> Job | None:
        job = self._jobs.get(self._by_key.get(key, ""))
        if job is not None:
            self._expire_locked(job)
            if job.state != ERROR:
                return job
        return None

    def admits(self, key: str) -> bool:
        """Would `submit(key, ...)` be accepted right now? Lets a route refuse
        BEFORE paying for a decode; `submit` re-checks under the lock."""
        with self._lock:
            return (self._cached_locked(key) is not None
                    or self._inflight < self.max_inflight)

    def submit(self, key: str, work: Callable[[], dict]) -> tuple[Job, bool]:
        """-> (job, was_cached). A cached hit is any prior job for this key that
        has not failed; a failed one is discarded so a retry actually retries.
        Raises `Busy` when the work would be new and MAX_INFLIGHT is reached."""
        with self._lock:
            job = self._cached_locked(key)
            if job is not None:
                self._jobs.move_to_end(job.id)
                return job, job.state == DONE
            # Failed or evicted: drop the mapping and fall through to a rerun.
            self._by_key.pop(key, None)
            if self._inflight >= self.max_inflight:
                raise Busy()
            self._inflight += 1

            job = Job(id=uuid.uuid4().hex, key=key)
            self._jobs[job.id] = job
            self._by_key[key] = job.id
            self._evict_locked()

        def run() -> dict:
            with self._lock:
                job.state = RUNNING
                job.started = time.monotonic()
            try:
                result = work()
            except Exception as exc:                      # noqa: BLE001
                log.exception("digitize job %s failed", job.id)
                with self._lock:
                    self._inflight -= 1
                    if job.state == ERROR:                # timed out already
                        raise
                    job.state = ERROR
                    # `error` is the line the Studio throws at the user
                    # (digitizer.js: `throw new Error(job.error)`), so it is
                    # customer copy, not a repr. The raw form goes to `detail`
                    # alongside the traceback — a developer reading a job now
                    # sees strictly more than before. See errors.py.
                    job.error = customer_message(exc)
                    job.detail = raw_error(exc)
                    if show_tracebacks():
                        job.detail += "\n" + traceback.format_exc(limit=8)
                raise
            with self._lock:
                self._inflight -= 1
                if job.state == ERROR:                    # timed out: discard
                    return result
                job.result = result
                job.state = DONE
            return result

        job._future = self._pool.submit(run)
        return job, False

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                self._expire_locked(job)
                self._jobs.move_to_end(job_id)  # touch: recently-read stays warm
            return job

    def _expire_locked(self, job: Job) -> None:
        """Fail a RUNNING job past `timeout_s`. Checked lazily on read — the
        poll is the only place anyone is waiting for the answer."""
        if (job.state == RUNNING and job.started is not None
                and time.monotonic() - job.started > self.timeout_s):
            log.warning("digitize job %s passed %.0fs; reported failed", job.id, self.timeout_s)
            job.state = ERROR
            job.error = TIMED_OUT
            job.detail = f"TimeoutError: still running after {self.timeout_s:.0f}s"

    def _evict_locked(self) -> None:
        while len(self._jobs) > MAX_CACHED:
            old_id, old = self._jobs.popitem(last=False)
            if old.state in (QUEUED, RUNNING):
                # Never evict work in flight — put it back and stop trying, or
                # a burst of submissions would orphan a running job's result.
                self._jobs[old_id] = old
                self._jobs.move_to_end(old_id)
                break
            if self._by_key.get(old.key) == old_id:
                self._by_key.pop(old.key, None)

    def stats(self) -> dict:
        with self._lock:
            states: dict[str, int] = {}
            for j in self._jobs.values():
                states[j.state] = states.get(j.state, 0) + 1
            return {"jobs": len(self._jobs), "states": states, "inflight": self._inflight}

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
