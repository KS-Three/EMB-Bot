"""The digitizer service's customer-facing error paths and response shapes.

`test_service.py` pins the engine seams (edits, caches, sizes on the machine).
This file pins what a customer meets when something is WRONG with what they
sent — a PDF instead of a PNG, a 30 MB photo, a one-pixel logo, a format the
service does not write — and that the happy path keeps the shape Studio reads.

For every rejection the assertions are on the status code AND the sentence:
the Studio shows `detail` / `error` verbatim, so a code with a stack-trace
sentence is a bug even when the status is right.

Everything runs against the real app through the real routes (no mocked
pipeline). The few jobs that run the pipeline use tiny art (~1-2 s each).

Real defects found while writing this are `xfail`ed with the reason, not
fixed here (tests only); each is listed in the PR body.
"""
from __future__ import annotations

import json
import time

import cv2
import numpy as np
import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from digitizer_service.app import MAX_PIXELS, MAX_UPLOAD_BYTES  # noqa: E402
from digitizer_service.formats import FORMATS  # noqa: E402

_NOT_AN_IMAGE = "isn't an image the engine can read"


def _png(arr: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", arr)
    assert ok
    return buf.tobytes()


def _logo(size: int = 60) -> bytes:
    """A black square on white: the cheapest art that digitizes to something."""
    img = np.full((size, size, 3), 255, np.uint8)
    m = size // 6
    cv2.rectangle(img, (m, m), (size - m, size - m), (0, 0, 0), -1)
    return _png(img)


def _submit(client, data: bytes, config: dict | str | None = None, name="art.png"):
    form = {}
    if config is not None:
        form["config"] = config if isinstance(config, str) else json.dumps(config)
    return client.post("/digitize", files={"image": (name, data, "image/png")}, data=form)


def _wait(client, job_id: str) -> dict:
    for _ in range(600):
        state = client.get(f"/jobs/{job_id}").json()
        if state["state"] in ("done", "error"):
            return state
        time.sleep(0.1)
    raise AssertionError(f"job {job_id} never finished")


def _run(client, data: bytes, config: dict | None = None) -> dict:
    r = _submit(client, data, config)
    assert r.status_code == 202, r.text
    return _wait(client, r.json()["job_id"])


# --- unsupported / corrupt uploads: 400 at submit, with the next move -------

@pytest.mark.parametrize("name,payload", [
    ("pdf", b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n"),
    ("svg", b"<svg xmlns='http://www.w3.org/2000/svg' width='10' height='10'/>"),
    ("text", b"hello there"),
    ("jpeg-header-then-garbage", b"\xff\xd8\xff\xe0not really a jpeg"),
    ("random-bytes", bytes(range(256)) * 8),
])
def test_unreadable_upload_is_a_clear_400_that_names_what_works(client, name, payload):
    r = _submit(client, payload, name=f"art.{name}")
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert _NOT_AN_IMAGE in detail
    assert "PNG, JPEG, WebP and TIFF" in detail          # the next move
    assert "PDF and SVG" in detail                        # the common mistakes, named


def test_truncated_png_is_a_clear_400_not_a_crash(client):
    r = _submit(client, _logo()[:40])
    assert r.status_code == 400
    assert _NOT_AN_IMAGE in r.json()["detail"]


def test_a_rejected_upload_never_creates_a_job(client):
    before = client.get("/health").json()["jobs"]
    _submit(client, b"%PDF-1.4 nope")
    assert client.get("/health").json()["jobs"] == before


def test_empty_upload_says_no_image_received(client):
    r = _submit(client, b"")
    assert r.status_code == 400
    assert r.json()["detail"] == "No image received."


# --- oversize ---------------------------------------------------------------

def test_upload_over_the_byte_limit_is_a_413_that_names_the_limit(client):
    r = _submit(client, b"\0" * (MAX_UPLOAD_BYTES + 1))
    assert r.status_code == 413
    detail = r.json()["detail"]
    assert f"limit is {MAX_UPLOAD_BYTES // 1024 // 1024} MB" in detail
    assert "smaller" in detail


@pytest.mark.xfail(reason=(
    "DEFECT: the 413 message floors both sizes to whole MB, so a 12.0001 MB "
    "upload is reported as 'Artwork is 12 MB; the limit is 12 MB' — it "
    "contradicts itself. app.start_digitize / calibration_read use "
    "len(data)//1024//1024; round up or show one decimal."), strict=False)
def test_byte_limit_message_does_not_say_the_file_is_exactly_the_limit(client):
    r = _submit(client, b"\0" * (MAX_UPLOAD_BYTES + 1))
    assert r.status_code == 413
    detail = r.json()["detail"]
    limit_mb = MAX_UPLOAD_BYTES // 1024 // 1024
    assert f"Artwork is {limit_mb} MB; the limit is {limit_mb} MB" not in detail


def test_upload_exactly_at_the_byte_limit_is_not_a_413(client):
    # Boundary: the gate is `>`, so a file AT the limit proceeds to decode
    # and fails there (it is zeros, not an image) — a 400, not a 413.
    r = _submit(client, b"\0" * MAX_UPLOAD_BYTES)
    assert r.status_code == 400
    assert _NOT_AN_IMAGE in r.json()["detail"]


def test_image_over_the_pixel_limit_is_a_413_that_gives_a_target_size(client):
    # 6000x7000 = 42 MP; a flat PNG of that size is only a few KB on the wire.
    side_a, side_b = 6000, 7000
    assert side_a * side_b > MAX_PIXELS
    data = _png(np.zeros((side_b, side_a), np.uint8))
    assert len(data) < MAX_UPLOAD_BYTES, "fixture must trip the pixel gate, not the byte gate"
    r = _submit(client, data)
    assert r.status_code == 413
    detail = r.json()["detail"]
    assert "6000x7000" in detail
    assert f"limit is {MAX_PIXELS // 1_000_000}" in detail
    assert "2000 px across" in detail                      # the next move


def test_health_advertises_the_same_limits_the_gates_enforce(client):
    limits = client.get("/health").json()["limits"]
    assert limits == {"max_upload_bytes": MAX_UPLOAD_BYTES, "max_pixels": MAX_PIXELS}


# --- missing / malformed fields --------------------------------------------

def test_digitize_without_an_image_part_is_a_422_naming_the_field(client):
    r = client.post("/digitize", data={"config": "{}"})
    assert r.status_code == 422
    errs = r.json()["detail"]
    assert errs[0]["loc"] == ["body", "image"]
    assert errs[0]["type"] == "missing"


def test_digitize_with_no_body_at_all_is_a_422_not_a_500(client):
    assert client.post("/digitize").status_code == 422


@pytest.mark.parametrize("config,fragment", [
    ("{not json", "config is not valid JSON"),
    ("[1, 2]", "config must be a JSON object"),
    ('"a string"', "config must be a JSON object"),
    ('{"no_such_field": 1}', "unknown config field(s): no_such_field"),
])
def test_bad_config_is_a_400_that_says_what_is_wrong(client, config, fragment):
    r = _submit(client, _logo(), config)
    assert r.status_code == 400
    assert fragment in r.json()["detail"]


def test_config_is_validated_before_the_image_is_decoded(client):
    # Both are wrong; the caller hears about the config (cheap check first).
    r = _submit(client, b"%PDF-1.4", '{"no_such_field": 1}')
    assert r.status_code == 400
    assert "no_such_field" in r.json()["detail"]


@pytest.mark.xfail(reason=(
    "DEFECT: target_width_mm is not validated at submit. 0 and 'wide' are "
    "accepted with a 202 and the JOB later fails with a raw "
    "'ZeroDivisionError: float division by zero' / "
    "\"ValueError: could not convert string to float: 'wide'\" (stage1_prep "
    "line ~418); -5 is accepted and the job even completes. Expected a 400 "
    "naming target_width_mm, like the unknown-field case."), strict=False)
@pytest.mark.parametrize("width", [0, -5, "wide"])
def test_nonsense_target_width_is_a_400_at_submit(client, width):
    r = _submit(client, _logo(), {"target_width_mm": width})
    assert r.status_code == 400
    assert "target_width_mm" in r.json()["detail"]


def test_unknown_job_id_is_a_404_with_a_sentence(client):
    r = client.get("/jobs/does-not-exist")
    assert r.status_code == 404
    assert "No such job" in r.json()["detail"]


# --- very small / empty art: a job error written for a customer -------------

@pytest.mark.parametrize("name,arr", [
    ("1x1-black", np.zeros((1, 1, 3), np.uint8)),
    ("blank-white", np.full((200, 200, 3), 255, np.uint8)),
    ("fully-transparent", np.zeros((80, 80, 4), np.uint8)),
])
def test_art_with_nothing_to_stitch_fails_the_job_in_plain_language(client, name, arr):
    r = _submit(client, _png(arr))
    assert r.status_code == 202, "the decode gate passes; the failure is the job's"
    state = _wait(client, r.json()["job_id"])
    assert state["state"] == "error"
    err = state["error"]
    assert "nothing to stitch" in err
    assert "crop tighter" in err                           # the next move
    for leak in ("ValueError", "Traceback", "foreground pixels"):
        assert leak not in err, "engine jargon reached the customer sentence"
    assert "design" not in state                           # no half-result alongside the error
    assert "Traceback" in state["detail"], "the developer detail keeps the trace"


def test_a_small_but_real_logo_digitizes(client):
    state = _run(client, _logo(60))
    assert state["state"] == "done"
    assert len(state["design"]["stitches"]) > 0


# --- /digitize happy path: the shape Studio reads ---------------------------

def test_submit_response_shape(client):
    r = _submit(client, _logo(), {"target_width_mm": 40.0})
    assert r.status_code == 202
    body = r.json()
    assert set(body) == {"job_id", "state", "cached"}
    assert isinstance(body["job_id"], str) and body["job_id"]
    assert body["state"] in ("queued", "running", "done")
    assert isinstance(body["cached"], bool)
    _wait(client, body["job_id"])


def test_finished_job_carries_the_full_payload_shape(client):
    state = _run(client, _logo(), {"target_width_mm": 40.0})
    assert state["state"] == "done"
    assert {"job_id", "design", "review", "stats", "warnings",
            "preflight", "generation_cache"} <= set(state)

    design = state["design"]
    assert {"stitches", "colors", "runs", "stitchCount", "colorCount",
            "name", "widthMM", "heightMM"} <= set(design)
    assert design["stitchCount"] > 0
    assert design["colorCount"] == len(design["colors"]) >= 1
    for s in design["stitches"][:50]:
        assert {"x", "y", "type"} <= set(s)
        assert isinstance(s["x"], int) and isinstance(s["y"], int)
    assert design["stitches"][-1]["type"] == "end"
    for c in design["colors"]:
        assert {"r", "g", "b"} <= set(c)

    assert {"stitch_count", "color_changes", "size_mm", "blocks"} <= set(state["stats"])
    assert {"palette", "shapes", "design_size_mm"} <= set(state["review"])
    assert isinstance(state["warnings"], list)
    assert state["generation_cache"] in ("hit", "miss")


def test_an_identical_resubmit_is_served_from_the_job_cache(client):
    cfg = {"target_width_mm": 40.0}
    first = _submit(client, _logo(), cfg)
    _wait(client, first.json()["job_id"])
    second = _submit(client, _logo(), cfg)
    assert second.status_code == 202
    assert second.json()["cached"] is True
    assert second.json()["job_id"] == first.json()["job_id"]


# --- /export ---------------------------------------------------------------

_HAND_DESIGN = {
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


def test_unknown_export_format_lists_what_is_supported(client):
    r = client.post("/export", json={"design": _HAND_DESIGN, "format": "gif"})
    assert r.status_code == 400
    detail = r.json()["detail"]
    assert "unsupported format 'gif'" in detail
    for fmt in FORMATS:
        assert fmt in detail, f"{fmt} missing from the supported list"


@pytest.mark.parametrize("fmt", ["DST", ".dst", ".Dst"])
def test_export_format_is_case_and_dot_insensitive(client, fmt):
    r = client.post("/export", json={"design": _HAND_DESIGN, "format": fmt})
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('.dst"')


def test_export_defaults_to_dst_when_no_format_is_given(client):
    r = client.post("/export", json={"design": _HAND_DESIGN})
    assert r.status_code == 200
    assert r.headers["content-disposition"].endswith('.dst"')


@pytest.mark.parametrize("payload", [
    {"format": "dst"},
    {"design": None, "format": "dst"},
    {"design": "a string", "format": "dst"},
    {"design": [], "format": "dst"},
    {"design": {}, "format": "dst"},
    {"design": {"stitches": []}, "format": "dst"},
])
def test_export_without_a_usable_design_is_a_400_naming_the_field(client, payload):
    r = client.post("/export", json=payload)
    assert r.status_code == 400
    assert "payload.design must be a design with stitches" in r.json()["detail"]


@pytest.mark.parametrize("payload", [
    [1, 2, 3],
    "just a string",
])
def test_export_with_a_non_object_body_is_a_422(client, payload):
    assert client.post("/export", json=payload).status_code == 422


def test_export_with_a_non_json_body_is_a_422(client):
    r = client.post("/export", content=b"not json",
                    headers={"content-type": "application/json"})
    assert r.status_code == 422


@pytest.mark.parametrize("stitch", [{"x": "abc", "y": 1, "type": "stitch"},
                                    {"y": 1, "type": "stitch"}])
def test_export_with_a_malformed_stitch_dict_is_a_400_naming_the_format(client, stitch):
    design = dict(_HAND_DESIGN, stitches=[stitch])
    r = client.post("/export", json={"design": design, "format": "dst"})
    assert r.status_code == 400
    assert r.json()["detail"].startswith("could not write dst:")


@pytest.mark.xfail(reason=(
    "DEFECT: /export catches (KeyError, TypeError, ValueError) but "
    "adapter.design_to_pattern raises AttributeError ('list' object has no "
    "attribute 'get') when a stitch is a bare [x, y, flag] list instead of a "
    "dict, so the caller gets a bare 500 'Internal Server Error' with no "
    "sentence. Expected the same 400 'could not write dst: ...' as a bad dict."),
    strict=False)
@pytest.mark.parametrize("stitches", [[[0, 0, 0], [10, 10, 0]], ["x", "y"], [1, 2]])
def test_export_with_non_dict_stitches_is_a_400_not_a_500(client, stitches):
    # Today the shared client re-raises the server's AttributeError (the real
    # server answers a bare 500); either way this does not reach the 400. Do
    # NOT build a second TestClient here: tests/test_client_fixture_is_shared.py
    # forbids it (its lifespan exit kills the shared job executor).
    r = client.post("/export", json={"design": {"stitches": stitches}, "format": "dst"})
    assert r.status_code == 400


def test_export_response_shape_for_every_format(client):
    for fmt, meta in FORMATS.items():
        r = client.post("/export", json={"design": _HAND_DESIGN, "format": fmt,
                                         "label": "My Logo"})
        assert r.status_code == 200, (fmt, r.text)
        assert len(r.content) > 0, fmt
        assert r.headers["content-type"].split(";")[0] == meta["mime"], fmt
        assert r.headers["content-disposition"] == 'attachment; filename="My-Logo.%s"' % fmt
        assert r.headers["x-stitch-convention"] == meta["convention"]
        assert float(r.headers["x-design-width-mm"]) > 0
        assert float(r.headers["x-design-height-mm"]) > 0


def test_export_of_a_digitized_design_round_trips_through_the_job(client):
    design = _run(client, _logo(), {"target_width_mm": 40.0})["design"]
    r = client.post("/export", json={"design": design, "format": "pes", "label": ""})
    assert r.status_code == 200
    assert r.headers["content-disposition"] == 'attachment; filename="EMBBOT.pes"'
    assert r.content[:4] == b"#PES"


def test_health_lists_exactly_the_formats_export_accepts(client):
    listed = {f["format"] for f in client.get("/health").json()["formats"]}
    assert listed == set(FORMATS)
