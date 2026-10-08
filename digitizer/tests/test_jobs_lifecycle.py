"""`JobRegistry` lifecycle, driven directly with no HTTP: submit -> status ->
result -> failure -> eviction/cleanup.

`test_service.py` pins retry-after-failure, the error line, and that running
jobs are never evicted; PR #694 pins the routes' sentences; PR #710 pins the
guards (timeout, in-flight bound, traceback hiding). This file pins the rest of
the state machine, and avoids anything #710 changes (exact `stats()` shape,
trace presence under a token), so it holds before and after that lands.

The registry holds no temp files — nothing in `jobs.py` touches disk — so
"cleanup" here is what it does own: dropping evicted jobs and their cache-key
mappings, so a resubmit reruns instead of pointing at a job that is gone.
"""
from __future__ import annotations

import threading

import pytest

from digitizer_service.jobs import (DONE, ERROR, MAX_CACHED, QUEUED, RUNNING,
                                    JobRegistry)


@pytest.fixture
def registry():
    reg = JobRegistry(workers=1)
    yield reg
    reg.shutdown()


def _block(registry, key="slow"):
    """Occupy the single worker; returns (job, release)."""
    started, release = threading.Event(), threading.Event()

    def work():
        started.set()
        release.wait(10)
        return {"ok": True}

    job, _ = registry.submit(key, work)
    assert started.wait(10)
    return job, release


def test_state_walks_queued_running_done(registry):
    running, release = _block(registry)
    queued, _ = registry.submit("next", lambda: {"n": 1})
    assert running.state == RUNNING
    assert queued.state == QUEUED
    release.set()
    queued._future.result(timeout=10)
    assert running.state == DONE and queued.state == DONE


def test_public_status_before_the_result_exists_has_no_payload(registry):
    running, release = _block(registry)
    queued, _ = registry.submit("next", lambda: {"design": "x"})
    for job, state in ((running, RUNNING), (queued, QUEUED)):
        assert job.public() == {"job_id": job.id, "state": state}
    release.set()
    queued._future.result(timeout=10)


def test_done_result_is_merged_into_the_public_view(registry):
    job, cached = registry.submit("k", lambda: {"design": {"n": 3}, "warnings": []})
    job._future.result(timeout=10)
    assert not cached
    assert job.public() == {"job_id": job.id, "state": DONE,
                            "design": {"n": 3}, "warnings": []}


def test_future_result_and_job_result_are_the_same_dict(registry):
    job, _ = registry.submit("k", lambda: {"a": 1})
    assert job._future.result(timeout=10) is job.result


def test_get_returns_the_job_and_none_for_an_unknown_id(registry):
    job, _ = registry.submit("k", lambda: {})
    assert registry.get(job.id) is job
    assert registry.get("no-such-id") is None


def test_resubmit_of_a_finished_key_is_a_cache_hit_that_never_reruns(registry):
    calls = []
    job, _ = registry.submit("k", lambda: calls.append(1) or {"a": 1})
    job._future.result(timeout=10)
    again, cached = registry.submit("k", lambda: calls.append(1) or {"a": 2})
    assert cached is True and again is job
    assert calls == [1]


def test_resubmit_while_in_flight_joins_the_job_but_is_not_called_cached(registry):
    running, release = _block(registry, key="k")
    again, cached = registry.submit("k", lambda: {"never": True})
    assert again is running
    assert cached is False, "cached means a finished result, not a running one"
    release.set()
    running._future.result(timeout=10)


def test_a_failed_job_is_error_with_a_traceback_and_no_result(registry, monkeypatch):
    monkeypatch.delenv("EMBBOT_SERVICE_TOKEN", raising=False)

    def boom():
        raise ValueError("bad art")

    job, _ = registry.submit("k", boom)
    with pytest.raises(ValueError):
        job._future.result(timeout=10)
    assert job.state == ERROR and job.result is None
    pub = job.public()
    assert set(pub) >= {"job_id", "state", "error", "detail"}
    assert "bad art" in pub["detail"]
    assert "Traceback" in pub["detail"]


def test_a_failure_does_not_poison_the_worker_for_the_next_job(registry):
    bad, _ = registry.submit("bad", lambda: 1 / 0)
    good, _ = registry.submit("good", lambda: {"ok": True})
    assert good._future.result(timeout=10) == {"ok": True}
    assert bad.state == ERROR and good.state == DONE


def test_a_failed_job_stays_readable_by_id_after_a_retry_replaces_its_key(registry):
    bad, _ = registry.submit("k", lambda: 1 / 0)
    bad._future.exception(timeout=10)
    retry, cached = registry.submit("k", lambda: {"ok": True})
    retry._future.result(timeout=10)
    assert retry.id != bad.id and not cached
    assert registry.get(bad.id).state == ERROR
    assert registry.get(retry.id).state == DONE


def test_eviction_drops_the_oldest_finished_job_and_its_cache_mapping(registry):
    first, _ = registry.submit("k0", lambda: {"n": 0})
    first._future.result(timeout=10)
    for i in range(1, MAX_CACHED + 1):
        registry.submit(f"k{i}", lambda: {"n": 1})[0]._future.result(timeout=10)

    assert registry.get(first.id) is None, "oldest finished job should be evicted"
    assert registry.stats()["jobs"] == MAX_CACHED
    # The key mapping went with it: a resubmit reruns rather than returning
    # a job nobody can look up.
    again, cached = registry.submit("k0", lambda: {"n": 99})
    assert not cached and again.id != first.id
    assert again._future.result(timeout=10) == {"n": 99}


def test_reading_a_job_keeps_it_warm_through_eviction(registry):
    keep, _ = registry.submit("keep", lambda: {})
    keep._future.result(timeout=10)
    for i in range(MAX_CACHED - 1):
        registry.submit(f"k{i}", lambda: {})[0]._future.result(timeout=10)
    registry.get(keep.id)                           # touch: now most recent
    for i in range(5):
        registry.submit(f"late{i}", lambda: {})[0]._future.result(timeout=10)
    assert registry.get(keep.id) is keep


def test_stats_counts_jobs_by_state(registry):
    running, release = _block(registry)
    registry.submit("q", lambda: {})
    done, _ = registry.submit("d", lambda: {})
    stats = registry.stats()
    assert stats["jobs"] == 3
    assert stats["states"] == {RUNNING: 1, QUEUED: 2}
    release.set()
    done._future.result(timeout=10)
    assert registry.stats()["states"] == {DONE: 3}


def test_shutdown_cancels_queued_work_and_leaves_the_running_job_alone():
    reg = JobRegistry(workers=1)
    running, release = _block(reg)
    queued, _ = reg.submit("q", lambda: {"never": True})
    reg.shutdown()
    assert queued._future.cancelled()
    assert queued.public() == {"job_id": queued.id, "state": QUEUED}
    release.set()
    assert running._future.result(timeout=10) == {"ok": True}
