"""A customer cancels a running digitize: `POST /jobs/{id}/cancel`.

A job runs 60 to 600 s and until 2026-11-12 the only ways out were to wait or
to reload. A cancel rides the mechanism the job deadline built
(`digitizer_core.deadline`, `tests/test_service.py`'s deadline section): the
registry sets a flag, the worker reads it at the next stage seam, and stops.
A poller reads `cancelled` -- a state, not an error.
"""
from __future__ import annotations

import json
import threading
import time
from pathlib import Path

import pytest

pytest.importorskip("fastapi", reason="service extra not installed")
from digitizer_core import deadline  # noqa: E402
from digitizer_service.jobs import JobRegistry  # noqa: E402

from .conftest import wait_for_job  # noqa: E402

ART = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"


def _staged_work(stages: int, stage_s: float, ran: list, entered: threading.Event | None = None):
    """A stand-in pipeline: `stages` seams `stage_s` apart, each recorded in
    `ran`, each checking the way the real stages do. `entered` is set once
    the worker is inside the first stage."""
    def work() -> dict:
        for i in range(stages):
            deadline.check(f"stage {i}")
            if entered is not None:
                entered.set()
            time.sleep(stage_s)
            ran.append(i)
        return {"stages": len(ran)}
    return work


# --- the registry ------------------------------------------------------------

def test_cancel_mid_job_stops_it_at_the_next_seam_and_says_cancelled_not_error():
    registry = JobRegistry(workers=1, timeout_s=60.0)
    ran: list = []
    entered = threading.Event()
    job, _ = registry.submit("slow", _staged_work(40, 0.1, ran, entered))
    assert entered.wait(5)

    assert registry.cancel(job.id) is job
    # The verdict is immediate for a poller; the worker follows at the seam.
    assert job.public() == {"job_id": job.id, "state": "cancelled"}

    exc = job._future.exception(timeout=10)
    assert isinstance(exc, deadline.Cancelled)
    assert isinstance(exc, deadline.Abandoned)      # unwinds like a deadline does
    # Cancelled inside stage 0: that stage finishes (it cannot be interrupted)
    # and the seam before stage 1 stops the job. One stage, not forty.
    assert len(ran) <= 2, f"kept computing {len(ran)} stages after the cancel"
    assert registry.stats()["inflight"] == 0
    # Still one verdict in the same words after the worker stopped.
    assert registry.get(job.id).public() == {"job_id": job.id, "state": "cancelled"}
    registry.shutdown()


def test_the_next_job_starts_promptly_after_a_cancel():
    """What the cancel is for: the customer's next upload does not queue
    behind the rest of a job nobody wants (4 s of it here)."""
    registry = JobRegistry(workers=1, timeout_s=60.0)
    entered = threading.Event()
    slow, _ = registry.submit("slow", _staged_work(40, 0.1, [], entered))
    assert entered.wait(5)
    registry.cancel(slow.id)

    t0 = time.monotonic()
    fast, _ = registry.submit("fast", lambda: {"ok": True})
    assert fast._future.result(timeout=10) == {"ok": True}
    waited = time.monotonic() - t0
    assert fast.state == "done"
    assert waited < 1.0, f"the next job waited {waited:.1f}s behind a cancelled one"
    registry.shutdown()


def test_cancelling_a_queued_job_never_runs_its_work():
    registry = JobRegistry(workers=1, timeout_s=60.0)
    release = threading.Event()
    first, _ = registry.submit("first", lambda: release.wait(10) and {"ok": True})
    ran: list = []
    queued, _ = registry.submit("queued", _staged_work(3, 0.0, ran))
    assert queued.state == "queued"

    assert registry.cancel(queued.id).state == "cancelled"
    release.set()
    first._future.result(timeout=10)
    assert isinstance(queued._future.exception(timeout=10), deadline.Cancelled)
    assert ran == []
    assert queued.state == "cancelled" and queued.started is None
    assert first.state == "done"
    assert registry.stats()["inflight"] == 0
    registry.shutdown()


def test_cancelling_an_unknown_job_is_harmless():
    registry = JobRegistry(workers=1)
    live, _ = registry.submit("live", lambda: {"ok": True})
    assert registry.cancel("no-such-job") is None
    assert live._future.result(timeout=10) == {"ok": True}
    assert registry.stats() == {"jobs": 1, "states": {"done": 1}, "inflight": 0}
    registry.shutdown()


def test_cancelling_a_finished_job_leaves_it_finished_and_cached():
    registry = JobRegistry(workers=1)
    job, _ = registry.submit("k", lambda: {"answer": 42})
    job._future.result(timeout=10)

    assert registry.cancel(job.id) is job
    assert job.public() == {"job_id": job.id, "state": "done", "answer": 42}
    again, cached = registry.submit("k", lambda: pytest.fail("a finished job must not rerun"))
    assert again is job and cached is True
    registry.shutdown()


def test_cancelling_a_failed_job_leaves_its_error_words_alone():
    registry = JobRegistry(workers=1)

    def boom() -> dict:
        raise ValueError("nope")

    job, _ = registry.submit("k", boom)
    job._future.exception(timeout=10)
    before = job.public()
    assert before["state"] == "error"
    assert registry.cancel(job.id) is job
    assert job.public() == before
    registry.shutdown()


def test_cancel_twice_is_the_same_as_once():
    registry = JobRegistry(workers=1, timeout_s=60.0)
    entered = threading.Event()
    job, _ = registry.submit("slow", _staged_work(40, 0.05, [], entered))
    assert entered.wait(5)
    assert registry.cancel(job.id).state == "cancelled"
    assert registry.cancel(job.id).state == "cancelled"
    job._future.exception(timeout=10)
    assert registry.cancel(job.id).state == "cancelled"
    assert registry.stats()["inflight"] == 0          # decremented once, not thrice
    registry.shutdown()


def test_the_same_request_after_a_cancel_runs_again_instead_of_replaying_the_cancel():
    """Pressing Auto Digitize again with nothing changed must digitize: a
    cancelled job is not a cache hit, even while its worker is still inside
    the stage the cancel could not interrupt."""
    registry = JobRegistry(workers=1, timeout_s=60.0)
    entered = threading.Event()
    first, _ = registry.submit("same", _staged_work(40, 0.1, [], entered))
    assert entered.wait(5)
    registry.cancel(first.id)

    second, cached = registry.submit("same", lambda: {"ok": True})
    assert second is not first and cached is False
    assert second._future.result(timeout=10) == {"ok": True}
    assert second.state == "done" and first.state == "cancelled"
    registry.shutdown()


def test_a_cancel_after_the_last_seam_still_reads_cancelled_and_keeps_no_result():
    """The flag is read at seams; work past its last one runs to the end.
    The poller was already told `cancelled`, so that stands and the result
    is dropped rather than turning a cancel into a late `done`."""
    registry = JobRegistry(workers=1, timeout_s=60.0)
    inside, release = threading.Event(), threading.Event()

    def work() -> dict:
        deadline.check("only seam")
        inside.set()
        release.wait(10)
        return {"late": True}

    job, _ = registry.submit("k", work)
    assert inside.wait(5)
    registry.cancel(job.id)
    release.set()
    assert job._future.result(timeout=10) == {"late": True}
    assert job.public() == {"job_id": job.id, "state": "cancelled"}
    assert registry.stats()["inflight"] == 0
    registry.shutdown()


def test_a_job_already_reported_timed_out_keeps_the_timeout_words_when_cancelled():
    from digitizer_service.jobs import TIMED_OUT

    registry = JobRegistry(workers=1, timeout_s=0.1)
    inside, release = threading.Event(), threading.Event()

    def work() -> dict:
        inside.set()
        release.wait(10)
        return {}

    job, _ = registry.submit("k", work)
    assert inside.wait(5)
    time.sleep(0.15)                                  # past the deadline, mid-stage
    assert registry.cancel(job.id).public()["error"] == TIMED_OUT
    release.set()
    job._future.result(timeout=10)
    assert job.state == "error"
    registry.shutdown()


def test_a_cancel_flag_alone_arms_no_deadline_and_leaves_nothing_behind():
    flag = threading.Event()
    with deadline.scope(None, cancel=flag):
        deadline.check("a")                           # not set: no-op
        assert deadline.remaining() is None
        flag.set()
        with pytest.raises(deadline.Cancelled) as caught:
            deadline.check("b")
        assert caught.value.stage == "b" and caught.value.over_s == 0.0
    deadline.check("c")                               # the scope left nothing armed


# --- over HTTP, on the real pipeline -----------------------------------------

def _submit(client, config: dict) -> str:
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps(config)})
    assert r.status_code == 202, r.text
    return r.json()["job_id"]


def test_over_http_a_cancel_mid_digitize_stops_the_real_pipeline_and_the_next_upload_runs(
        client, monkeypatch):
    """The wiring end to end: the worker's scope carries the registry's flag
    into the real `build_generation`, whose first seam stops the job. The
    worker is held just inside the job so the cancel provably lands mid-run."""
    import importlib

    # The module, not the FastAPI object the package re-exports as `app`.
    service = importlib.import_module("digitizer_service.app")
    registry = service.registry

    real = service.build_generation
    entered, go = threading.Event(), threading.Event()

    def held(*args, **kwargs):
        entered.set()
        go.wait(30)
        return real(*args, **kwargs)

    monkeypatch.setattr(service, "build_generation", held)
    job_id = _submit(client, {"target_width_mm": 43.7})
    assert entered.wait(60), registry.stats()         # queued behind other tests' jobs
    assert client.get(f"/jobs/{job_id}").json()["state"] == "running"

    r = client.post(f"/jobs/{job_id}/cancel")
    assert r.status_code == 200, r.text
    assert r.json() == {"job_id": job_id, "state": "cancelled"}
    monkeypatch.setattr(service, "build_generation", real)
    go.set()

    final = wait_for_job(client, job_id)
    assert final == {"job_id": job_id, "state": "cancelled"}   # no error, no detail, no design

    # The next upload runs, and the same request digitizes afresh.
    t0 = time.monotonic()
    again = _submit(client, {"target_width_mm": 43.7})
    assert again != job_id
    done = wait_for_job(client, again)
    assert done["state"] == "done", done
    assert done["stats"]["stitch_count"] > 0
    assert time.monotonic() - t0 < 60.0
    assert client.get(f"/jobs/{job_id}").json()["state"] == "cancelled"


def test_over_http_cancelling_an_unknown_job_is_a_404_and_changes_nothing(client):
    before = client.get("/health").json()["jobs"]["jobs"]
    r = client.post("/jobs/not-a-job/cancel")
    assert r.status_code == 404
    assert "detail" in r.json()
    assert client.get("/health").json()["jobs"]["jobs"] == before


def test_over_http_cancelling_a_finished_job_keeps_its_result(client):
    job_id = _submit(client, {"target_width_mm": 44.3})
    done = wait_for_job(client, job_id)
    assert done["state"] == "done", done

    r = client.post(f"/jobs/{job_id}/cancel")
    assert r.status_code == 200
    assert r.json() == {"job_id": job_id, "state": "done"}     # the state alone
    assert client.get(f"/jobs/{job_id}").json() == done
    # ...and the same request is still the free replay it was.
    with ART.open("rb") as f:
        replay = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                             data={"config": json.dumps({"target_width_mm": 44.3})}).json()
    assert replay == {"job_id": job_id, "state": "done", "cached": True}


def test_the_cancel_route_is_behind_the_token_like_the_poll(client, monkeypatch):
    monkeypatch.setenv("EMBBOT_SERVICE_TOKEN", "s3cret")
    assert client.post("/jobs/whatever/cancel").status_code == 401
    r = client.post("/jobs/whatever/cancel", headers={"X-EMBBOT-Token": "s3cret"})
    assert r.status_code == 404


def test_health_reports_the_version_the_cancel_route_arrived_in(client):
    major, minor, _patch = (int(x) for x in client.get("/health").json()["version"].split("."))
    assert (major, minor) >= (0, 7)
