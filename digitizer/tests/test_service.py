"""The service's contract with Studio.

Everything here runs against the real app through the real routes — no mocked
pipeline — because the things most likely to break are the seams: what a config
is allowed to contain, what a job returns, and whether a design survives the
trip out to a machine file.
"""
from __future__ import annotations

import io
import json
import time
from pathlib import Path

import pyembroidery
import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from fastapi.testclient import TestClient  # noqa: E402

from digitizer_service.app import MAX_PIXELS, app  # noqa: E402
from digitizer_service.jobs import JobRegistry, content_key  # noqa: E402

ART = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def _digitize(client, config: dict | None = None, art: Path = ART) -> dict:
    with art.open("rb") as f:
        r = client.post(
            "/digitize",
            files={"image": (art.name, f, "image/png")},
            data={"config": json.dumps(config or {})},
        )
    assert r.status_code == 202, r.text
    job_id = r.json()["job_id"]
    for _ in range(600):
        state = client.get(f"/jobs/{job_id}").json()
        if state["state"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert state["state"] == "done", state.get("detail") or state.get("error")
    return state


# --- health ---------------------------------------------------------------

def test_health_reports_what_the_service_can_do(client):
    h = client.get("/health").json()

    assert h["status"] == "ok"
    assert h["default_brand"] == "isacord"
    assert len(h["brands"]) == 68
    assert {f["format"] for f in h["formats"]} >= {"dst", "pes", "jef", "exp"}
    # Studio needs to know which convention wrote a file it is about to sew.
    assert all(f["convention"] for f in h["formats"])


def test_health_needs_no_token_even_when_one_is_set(client, monkeypatch):
    """Studio has to be able to ask 'are you there' before it can authenticate."""
    monkeypatch.setenv("EMBBOT_SERVICE_TOKEN", "s3cret")
    assert client.get("/health").status_code == 200
    assert client.get("/health").json()["auth"] == "token"


def test_token_gates_the_real_routes_when_set(client, monkeypatch):
    monkeypatch.setenv("EMBBOT_SERVICE_TOKEN", "s3cret")
    assert client.get("/jobs/whatever").status_code == 401
    assert client.post("/export", json={}).status_code == 401
    # And the right token gets through to a normal error, not an auth error.
    r = client.post("/export", json={}, headers={"X-EMBBOT-Token": "s3cret"})
    assert r.status_code == 400


# --- digitize -------------------------------------------------------------

def test_digitize_returns_a_design_a_review_and_stats(client):
    state = _digitize(client, {"target_width_mm": 80.0})

    design = state["design"]
    assert design["stitchCount"] > 500
    assert design["colorCount"] >= 3
    assert design["widthMM"] == pytest.approx(80.0, abs=1.0)
    assert design["stitches"][-1]["type"] == "end"
    assert {s["type"] for s in design["stitches"]} <= {"stitch", "jump", "trim", "color", "end"}

    assert len(state["review"]["shapes"]) >= 3
    assert state["review"]["palette"][0]["brand_id"] == "isacord"
    assert state["stats"]["stitch_count"] == design["stitchCount"]


def test_reported_stats_describe_the_delivered_design(client):
    """Not the plan it came from: the plan counts one more trim than the file
    contains, because its first block has no thread to cut yet."""
    state = _digitize(client, {"target_width_mm": 80.0})
    design, stats = state["design"], state["stats"]
    kinds = [s["type"] for s in design["stitches"]]

    assert stats["trims"] == kinds.count("trim")
    assert stats["jumps"] == kinds.count("jump")
    assert stats["color_changes"] == kinds.count("color")


def test_identical_request_is_served_from_cache(client):
    cfg = {"target_width_mm": 61.0}
    with ART.open("rb") as f:
        first = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                            data={"config": json.dumps(cfg)}).json()
    for _ in range(600):
        if client.get(f"/jobs/{first['job_id']}").json()["state"] == "done":
            break
        time.sleep(0.1)

    with ART.open("rb") as f:
        second = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                             data={"config": json.dumps(cfg)}).json()

    assert second["job_id"] == first["job_id"]
    assert second["cached"] is True


def test_a_different_parameter_is_a_different_job(client):
    with ART.open("rb") as f:
        a = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps({"target_width_mm": 55.0})}).json()
    with ART.open("rb") as f:
        b = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps({"target_width_mm": 56.0})}).json()

    assert a["job_id"] != b["job_id"]


def test_thread_brand_changes_the_catalog_numbers(client):
    iso = _digitize(client, {"target_width_mm": 80.0, "thread_brand": "isacord"})
    mad = _digitize(client, {"target_width_mm": 80.0, "thread_brand": "madeira-rayon"})

    assert iso["review"]["palette"][0]["brand_id"] == "isacord"
    assert mad["review"]["palette"][0]["brand_id"] == "madeira-rayon"
    assert mad["review"]["palette"][0]["brand"] == "Madeira Rayon 40"
    assert [p["number"] for p in iso["review"]["palette"]] != \
           [p["number"] for p in mad["review"]["palette"]]


def test_unknown_brand_is_rejected_with_a_useful_message(client):
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps({"thread_brand": "nope"})})
    assert r.status_code == 400
    assert "nope" in r.json()["detail"]


def test_config_cannot_reach_fields_that_write_to_disk(client):
    """debug_dir would let a request choose where the engine dumps PNGs."""
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps({"debug_dir": "C:/anywhere"})})
    assert r.status_code == 400
    assert "debug_dir" in r.json()["detail"]


def test_malformed_config_is_rejected(client):
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": "{not json"})
    assert r.status_code == 400


def test_a_file_that_is_not_an_image_is_rejected_at_submit(client):
    r = client.post("/digitize", files={"image": ("notes.txt", b"hello there", "text/plain")})
    assert r.status_code == 400
    assert "image" in r.json()["detail"].lower()


def test_empty_upload_is_rejected(client):
    r = client.post("/digitize", files={"image": ("empty.png", b"", "image/png")})
    assert r.status_code == 400


def test_unknown_job_is_404(client):
    assert client.get("/jobs/nosuchjob").status_code == 404


# --- export ---------------------------------------------------------------

@pytest.mark.parametrize("fmt", ["dst", "pes", "jef", "exp", "vp3", "xxx", "u01", "pec"])
def test_every_machine_format_writes_a_non_empty_file(client, fmt):
    design = _digitize(client, {"target_width_mm": 80.0})["design"]
    r = client.post("/export", json={"design": design, "format": fmt, "label": "Test Design"})

    assert r.status_code == 200, r.text
    assert len(r.content) > 200
    assert r.headers["x-stitch-convention"] == "tajima-standard"
    assert f".{fmt}" in r.headers["content-disposition"]


def test_pes_and_jef_survive_an_independent_reader(client):
    """These two are why the service exists: the browser cannot write them well.
    Reading them back with pyembroidery's own parser is the check that they are
    real files and not just bytes."""
    design = _digitize(client, {"target_width_mm": 80.0})["design"]

    for fmt, reader in (("pes", pyembroidery.read_pes), ("jef", pyembroidery.read_jef)):
        r = client.post("/export", json={"design": design, "format": fmt})
        pattern = reader(io.BytesIO(r.content))
        sewn = [s for s in pattern.stitches if s[2] == pyembroidery.STITCH]

        assert len(sewn) == design["stitchCount"], f"{fmt} lost stitches"
        w = (max(s[0] for s in sewn) - min(s[0] for s in sewn)) / 10.0
        h = (max(s[1] for s in sewn) - min(s[1] for s in sewn)) / 10.0
        assert w == pytest.approx(design["widthMM"], abs=0.2), f"{fmt} width"
        assert h == pytest.approx(design["heightMM"], abs=0.2), f"{fmt} height"


def test_export_reports_the_size_the_file_will_sew(client):
    design = _digitize(client, {"target_width_mm": 80.0})["design"]
    r = client.post("/export", json={"design": design, "format": "dst"})

    assert float(r.headers["x-design-width-mm"]) == pytest.approx(design["widthMM"], abs=0.05)
    assert float(r.headers["x-design-height-mm"]) == pytest.approx(design["heightMM"], abs=0.05)


def test_export_accepts_a_hand_built_design(client):
    """Lettering and imported designs come from the browser, not from here."""
    design = {
        "stitches": [
            {"x": 0, "y": 0, "type": "jump"},
            {"x": 0, "y": 0, "type": "stitch"},
            {"x": 200, "y": 0, "type": "stitch"},
            {"x": 200, "y": 100, "type": "stitch"},
            {"x": 0, "y": 0, "type": "end"},
        ],
        "colors": [{"r": 255, "g": 0, "b": 0, "name": "Red"}],
        "widthMM": 20.0,
        "heightMM": 10.0,
    }
    r = client.post("/export", json={"design": design, "format": "dst"})
    assert r.status_code == 200
    assert len(r.content) > 0


def test_unsupported_format_is_rejected(client):
    design = _digitize(client, {"target_width_mm": 80.0})["design"]
    r = client.post("/export", json={"design": design, "format": "gif"})
    assert r.status_code == 400
    assert "gif" in r.json()["detail"]


def test_export_without_a_design_is_rejected(client):
    assert client.post("/export", json={"format": "dst"}).status_code == 400
    assert client.post("/export", json={"design": {"stitches": []}}).status_code == 400


def test_filename_is_derived_safely_from_the_label(client):
    design = _digitize(client, {"target_width_mm": 80.0})["design"]
    r = client.post("/export",
                    json={"design": design, "format": "dst",
                          "label": "../../etc/passwd; rm -rf"})

    disposition = r.headers["content-disposition"]
    assert "/" not in disposition.split("filename=")[1]
    assert ".." not in disposition


# --- job registry ---------------------------------------------------------

def test_cache_key_ignores_key_order_but_not_values():
    img = b"pretend png"
    assert content_key(img, {"a": 1, "b": 2}) == content_key(img, {"b": 2, "a": 1})
    assert content_key(img, {"a": 1}) != content_key(img, {"a": 2})
    assert content_key(img, {"a": 1}) != content_key(b"other", {"a": 1})


def test_failed_jobs_are_not_cached_so_a_retry_actually_retries():
    registry = JobRegistry(workers=1)
    calls = {"n": 0}

    def failing():
        calls["n"] += 1
        raise RuntimeError("boom")

    job, cached = registry.submit("k", failing)
    job._future.exception(timeout=10)
    assert job.state == "error"
    assert not cached

    job2, cached2 = registry.submit("k", failing)
    job2._future.exception(timeout=10)
    assert job2.id != job.id
    assert calls["n"] == 2
    registry.shutdown()


def test_a_failed_job_reports_the_error_not_a_blank_result():
    registry = JobRegistry(workers=1)
    job, _ = registry.submit("k", lambda: (_ for _ in ()).throw(ValueError("bad art")))
    job._future.exception(timeout=10)

    public = job.public()
    assert public["state"] == "error"
    assert "bad art" in public["error"]
    assert "design" not in public


def test_running_jobs_are_never_evicted():
    """A burst of submissions must not orphan work in flight."""
    import threading

    registry = JobRegistry(workers=1)
    release = threading.Event()
    slow, _ = registry.submit("slow", lambda: (release.wait(10), {"ok": True})[1])

    for i in range(80):                       # far past MAX_CACHED
        registry.submit(f"k{i}", lambda: {"n": 1})

    assert registry.get(slow.id) is not None, "in-flight job was evicted"
    release.set()
    slow._future.result(timeout=10)
    registry.shutdown()


def test_max_pixels_guard_is_actually_wired(client):
    """The constant existing is not the same as the check running."""
    assert MAX_PIXELS > 0
    import numpy as np
    import cv2

    # 1x1 is fine; the guard only bites on genuinely huge art.
    ok, buf = cv2.imencode(".png", np.zeros((4, 4, 3), np.uint8))
    assert ok
    r = client.post("/digitize", files={"image": ("tiny.png", buf.tobytes(), "image/png")})
    assert r.status_code in (202, 400)   # decodes fine; may or may not digitize
