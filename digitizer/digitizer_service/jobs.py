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
import threading
import traceback
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


@dataclass
class Job:
    id: str
    key: str
    state: str = QUEUED
    result: dict | None = None
    error: str | None = None
    detail: str | None = None
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


class JobRegistry:
    def __init__(self, workers: int = 1):
        self._lock = threading.Lock()
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._by_key: dict[str, str] = {}
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="digitize")

    def submit(self, key: str, work: Callable[[], dict]) -> tuple[Job, bool]:
        """-> (job, was_cached). A cached hit is any prior job for this key that
        has not failed; a failed one is discarded so a retry actually retries."""
        with self._lock:
            existing_id = self._by_key.get(key)
            if existing_id:
                job = self._jobs.get(existing_id)
                if job is not None and job.state != ERROR:
                    self._jobs.move_to_end(job.id)
                    return job, job.state == DONE
                # Failed or evicted: drop the mapping and fall through to a rerun.
                self._by_key.pop(key, None)

            job = Job(id=uuid.uuid4().hex, key=key)
            self._jobs[job.id] = job
            self._by_key[key] = job.id
            self._evict_locked()

        def run() -> dict:
            with self._lock:
                job.state = RUNNING
            try:
                result = work()
            except Exception as exc:                      # noqa: BLE001
                with self._lock:
                    job.state = ERROR
                    job.error = f"{type(exc).__name__}: {exc}"
                    job.detail = traceback.format_exc(limit=8)
                raise
            with self._lock:
                job.result = result
                job.state = DONE
            return result

        job._future = self._pool.submit(run)
        return job, False

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                self._jobs.move_to_end(job_id)  # touch: recently-read stays warm
            return job

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
            return {"jobs": len(self._jobs), "states": states}

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
