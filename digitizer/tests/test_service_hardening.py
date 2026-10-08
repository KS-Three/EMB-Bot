"""The service's guards for a customer-facing deployment: body size, request
deadline, job timeout, in-flight bound, and no stack traces in responses.

`test_service_errors.py` (PR #694) pins the error SENTENCES of the routes; this
file pins the guards around them and does not re-test what that one covers.
Three of its xfails are fixed by this change and will XPASS: the 413 message
that flooring made contradict itself, `target_width_mm` validated at submit,
and a bare-list stitch on `/export` as a 400 rather than a 500.

The middlewares are pinned on a throwaway app with small budgets, so no test
here has to allocate 30 MB or wait two minutes. The registry is pinned on
fresh instances: the app's own is a session-wide singleton (see conftest).
"""
from __future__ import annotations

import json
import sys
import threading
import time

import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from fastapi import Body, FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import digitizer_service.app  # noqa: E402,F401
from digitizer_service.guards import BodyLimit, Deadline  # noqa: E402
from digitizer_service.jobs import ERROR, TIMED_OUT, Busy, JobRegistry  # noqa: E402

# `digitizer_service/__init__` re-exports the FastAPI object as `app`, which
# shadows the submodule on attribute access; take the module itself.
service = sys.modules["digitizer_service.app"]


def _guarded_app(limit: int = 1000, seconds: float = 0.3) -> FastAPI:
    a = FastAPI()

    @a.post("/echo")
    def echo(payload: dict = Body(...)) -> dict:
        return {"keys": len(payload)}

    @a.get("/slow-sync")
    def slow_sync() -> dict:
        time.sleep(2.0)                    # parked in the threadpool
        return {"ok": True}

    @a.get("/slow-async")
    async def slow_async() -> dict:
        import asyncio
        await asyncio.sleep(2.0)
        return {"ok": True}

    a.add_middleware(BodyLimit, limit_for=lambda _path: (limit, limit))
    a.add_middleware(Deadline, seconds=lambda: seconds)
    return a


# --- request size -----------------------------------------------------------

def test_declared_oversize_body_is_a_413_before_the_route_runs():
    c = TestClient(_guarded_app(limit=1000))
    r = c.post("/echo", content=b"{" + b" " * 2000 + b"}",
               headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert "Export it smaller" in r.json()["detail"]


def test_chunked_oversize_body_is_cut_off_at_the_budget():
    # No Content-Length: the body is counted as it streams.
    def chunks():
        yield b'{"a": "'
        for _ in range(50):
            yield b"x" * 100
        yield b'"}'
    c = TestClient(_guarded_app(limit=1000))
    r = c.post("/echo", content=chunks(), headers={"content-type": "application/json"})
    assert r.status_code == 413
    assert "over the limit" in r.json()["detail"]


def test_a_body_under_the_budget_is_untouched():
    c = TestClient(_guarded_app(limit=1000))
    assert c.post("/echo", json={"a": 1, "b": 2}).json() == {"keys": 2}


def test_upload_routes_name_the_file_limit_not_the_framing_budget():
    budget, advertised = service._body_limit("/digitize")
    assert advertised == service.MAX_UPLOAD_BYTES < budget
    assert service._body_limit("/export")[0] == service.MAX_JSON_BYTES


# --- request deadline -------------------------------------------------------

@pytest.mark.parametrize("path", ["/slow-sync", "/slow-async"])
def test_a_request_past_its_deadline_is_a_504_without_waiting_for_it(path):
    c = TestClient(_guarded_app(seconds=0.3))
    t0 = time.monotonic()
    r = c.get(path)
    assert r.status_code == 504
    assert "took too long" in r.json()["detail"]
    # The threadpool handler sleeps 2 s and cannot be cancelled; the 504 must
    # not wait for it.
    assert time.monotonic() - t0 < 1.5


# --- no stack traces in responses -------------------------------------------

def test_an_unhandled_error_is_a_500_sentence_with_no_trace(monkeypatch):
    def boom(*_a, **_k):
        raise RuntimeError("secret detail at /srv/digitizer_core/adapter.py:123")
    monkeypatch.setattr(service, "design_to_pattern", boom)
    # Not a context manager: exiting one runs the shared app's shutdown.
    c = TestClient(service.app, raise_server_exceptions=False)
    r = c.post("/export", json={"design": {"stitches": [{"x": 0, "y": 0, "type": "stitch"}]}})
    assert r.status_code == 500
    body = r.text
    assert "Something went wrong on our side" in r.json()["detail"]
    for leak in ("Traceback", "RuntimeError", "secret", ".py"):
        assert leak not in body


def _failed_job(monkeypatch, token: str | None):
    if token:
        monkeypatch.setenv("EMBBOT_SERVICE_TOKEN", token)
    else:
        monkeypatch.delenv("EMBBOT_SERVICE_TOKEN", raising=False)
    reg = JobRegistry()

    def work():
        raise KeyError("thread_index")
    job, _ = reg.submit("k", work)
    with pytest.raises(KeyError):
        job._future.result(timeout=10)
    reg.shutdown()
    return job.public()


def test_a_deployed_service_keeps_tracebacks_out_of_the_job(monkeypatch):
    state = _failed_job(monkeypatch, token="t0k3n")
    assert state["state"] == ERROR
    assert state["detail"] == "KeyError: 'thread_index'"
    assert "Traceback" not in json.dumps(state)


def test_a_loopback_developer_service_still_gets_the_trace(monkeypatch):
    assert "Traceback" in _failed_job(monkeypatch, token=None)["detail"]


# --- job timeout ------------------------------------------------------------

def test_a_runaway_job_is_reported_failed_and_its_late_result_dropped():
    reg = JobRegistry(timeout_s=0.2)
    release = threading.Event()

    def work():
        release.wait(10)
        return {"design": "late"}
    job, _ = reg.submit("k", work)
    time.sleep(0.4)
    state = reg.get(job.id).public()
    assert state["state"] == ERROR
    assert state["error"] == TIMED_OUT
    release.set()
    job._future.result(timeout=10)
    assert reg.get(job.id).state == ERROR and "design" not in reg.get(job.id).public()
    assert reg.stats()["inflight"] == 0
    reg.shutdown()


def test_a_timed_out_key_is_retried_not_served_from_cache():
    reg = JobRegistry(timeout_s=0.1)
    release = threading.Event()
    job, _ = reg.submit("k", lambda: release.wait(10) and {})
    time.sleep(0.25)
    assert reg.get(job.id).state == ERROR          # a poll is what expires it
    release.set()
    job._future.result(timeout=10)
    again, cached = reg.submit("k", lambda: {"ok": 1})
    assert again.id != job.id and not cached
    assert again._future.result(timeout=10) == {"ok": 1}
    reg.shutdown()


# --- concurrency guard ------------------------------------------------------

def test_new_work_past_the_inflight_bound_is_refused():
    reg = JobRegistry(max_inflight=2)
    release = threading.Event()
    first, _ = reg.submit("a", lambda: release.wait(10) and {})
    reg.submit("b", lambda: {})                     # queued behind "a"
    with pytest.raises(Busy):
        reg.submit("c", lambda: {})
    assert not reg.admits("c")
    # An identical resubmit is the cache, not new work: still admitted.
    assert reg.admits("a")
    assert reg.submit("a", lambda: {})[0] is first
    release.set()
    first._future.result(timeout=10)
    deadline = time.monotonic() + 10
    while reg.stats()["inflight"] and time.monotonic() < deadline:
        time.sleep(0.02)
    assert reg.admits("c")
    reg.shutdown()


def test_a_busy_service_says_503_before_decoding_the_upload(client, monkeypatch):
    monkeypatch.setattr(service.registry, "max_inflight", 0)
    # A PDF would be a 400 at decode; the 503 proves the decode never ran.
    r = client.post("/digitize", files={"image": ("a.pdf", b"%PDF-1.4 nope", "image/png")})
    assert r.status_code == 503
    assert r.headers["retry-after"] == "30"
    assert "busy" in r.json()["detail"]


# --- bad input: clear 4xx (extends #694's target_width_mm cases) ------------

@pytest.mark.parametrize("width", ["NaN", "Infinity", "true", "1001", "null"])
def test_target_width_outside_the_sane_range_is_a_400_at_submit(client, width):
    r = client.post("/digitize", files={"image": ("a.png", b"\x89PNG", "image/png")},
                    data={"config": '{"target_width_mm": %s}' % width})
    assert r.status_code == 400
    assert "target_width_mm" in r.json()["detail"]


def test_upload_size_message_rounds_up_so_it_never_contradicts_itself():
    from digitizer_service.guards import too_large_detail
    limit = service.MAX_UPLOAD_BYTES
    assert too_large_detail(limit + 1, limit) == \
        "Upload is 12.1 MB; the limit is 12 MB. Export it smaller and try again."
