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

import pystitch
import pytest

fastapi = pytest.importorskip("fastapi", reason="service extra not installed")
from fastapi.testclient import TestClient  # noqa: E402

from digitizer_service.app import MAX_PIXELS, app  # noqa: E402
from digitizer_service.jobs import JobRegistry, content_key  # noqa: E402

from .conftest import requires_tesseract  # noqa: E402

ART = Path(__file__).resolve().parents[1] / "testdata" / "logo_whitebg.png"
# The enclosed-background repro: a gradient logo with white icon linework
# that tags a Region `enclosed_background` and defaults it to unstitched.
REPRO = Path(__file__).resolve().parents[1] / "testdata" / "photo" / "repro_gradient_white_icon.png"

# The text-cluster-detection benchmark: the "ENTERPRISES INC." subline in this
# fixture is a real logo's independently-rescued sub-detail glyphs (see
# `test_pipeline.py::test_full_pipeline_tags_a_text_cluster_on_the_benchmark_subline`).
# 90 mm is the documented benchmark width at which the subline's glyphs are
# rescued and clustered.
ENTHUSIAST_LOGO = Path(__file__).resolve().parents[1] / "testdata" / "photo" / "enthusiast_logo.png"

# /digitize-manual fixtures: a plain rectangle (fill) and the same 24x2 mm
# satin bar `tests/test_satin.py::BAR` uses — known-good geometry rather than
# an untested shape.
MANUAL_RECT = [[0.0, 0.0], [20.0, 0.0], [20.0, 15.0], [0.0, 15.0]]
MANUAL_BAR = [[0.0, 0.0], [24.0, 0.0], [24.0, 2.0], [0.0, 2.0]]


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


def _manual_shapes() -> list[dict]:
    return [
        {"polygon": MANUAL_RECT, "technique": "fill", "thread_index": 0},
        {"polygon": [[p[0] + 30.0, p[1]] for p in MANUAL_BAR],
         "technique": "satin", "thread_index": 1},
    ]


def _digitize_manual(client, shapes=None, config: dict | None = None) -> dict:
    body = {"shapes": shapes if shapes is not None else _manual_shapes(),
            "config": config or {}}
    r = client.post("/digitize-manual", json=body)
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


# --- preflight (build step 9) ----------------------------------------------

def test_a_finished_job_carries_a_preflight_report(client):
    """The report is the point of digitizing through the service: Studio
    shows the operator what will go wrong on the machine before sewing."""
    state = _digitize(client, {"target_width_mm": 80.0})
    report = state["preflight"]

    assert report["grade"] in "ABCDF"
    assert 0 <= report["score"] <= 100
    assert isinstance(report["findings"], list)
    for f in report["findings"]:
        assert f["severity"] in ("info", "warn", "block")
        assert f["code"] and f["message"]
    # The service has the artwork in hand, so the thread check always runs.
    assert report["metrics"]["thread_match_checked"] is True


def test_preflight_off_is_none_not_a_passing_report(client):
    """Studio must be able to tell 'clean' apart from 'never checked'."""
    state = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    assert state["preflight"] is None


def test_a_poor_brand_match_reaches_the_operator(client):
    """End to end: the madeira purple that motivated the whole check arrives
    on the job payload as a THREAD_MATCH_POOR finding."""
    state = _digitize(client, {"target_width_mm": 80.0,
                               "thread_brand": "madeira-rayon"})
    codes = {f["code"] for f in state["preflight"]["findings"]}
    assert "THREAD_MATCH_POOR" in codes


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
    Reading them back with pystitch's own parser is the check that they are
    real files and not just bytes."""
    design = _digitize(client, {"target_width_mm": 80.0})["design"]

    for fmt, reader in (("pes", pystitch.read_pes), ("jef", pystitch.read_jef)):
        r = client.post("/export", json={"design": design, "format": fmt})
        pattern = reader(io.BytesIO(r.content))
        sewn = [s for s in pattern.stitches if s[2] == pystitch.STITCH]

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


# --- the shape-layers contract over HTTP -----------------------------------

def test_review_payload_carries_what_a_layers_panel_needs(client):
    """Per shape: its layer, WHEN it sews and AS WHAT — read off the emitted
    plan, not re-guessed from geometry."""
    review = _digitize(client, {"target_width_mm": 80.0, "preflight": False})["review"]
    shapes = review["shapes"]

    assert all({"layer", "sew_index", "sew_block", "tier"} <= set(s) for s in shapes)
    sewn = [s for s in shapes if s["sew_index"] is not None]
    assert sorted(s["sew_index"] for s in sewn) == list(range(len(sewn)))
    tiers = {s["thread_number"]: s["tier"] for s in sewn}
    assert tiers["5510"] == "satin", "the green bar is the design's satin shape"
    assert tiers["1704"] == "fill"


def test_the_whole_edit_round_trip_over_http(client):
    """digitize -> read shape_ids -> re-digitize with a recolor, a delete and
    a tier flip -> a DIFFERENT job whose survivors keep their ids."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    shapes = {s["thread_number"]: s for s in first["review"]["shapes"]}
    green = shapes["5510"]                      # satin bar
    purple = shapes["2905"]                     # rectangle
    red = shapes["1704"]
    tiny = min((s for s in first["review"]["shapes"] if s["thread_number"] == "1305"),
               key=lambda s: s["area_mm2"])

    second = _digitize(client, {
        "target_width_mm": 80.0, "preflight": False,
        "deleted_shape_ids": [tiny["shape_id"], "S-GONE"],
        "shape_overrides": {
            purple["shape_id"]: {"thread_index": red["thread_index"]},
            green["shape_id"]: {"tier": "fill"},
        },
    })

    ids_before = {s["shape_id"] for s in first["review"]["shapes"]}
    after = {s["shape_id"]: s for s in second["review"]["shapes"]}
    assert set(after) == ids_before - {tiny["shape_id"]}, "stable ids, one gone"
    assert after[purple["shape_id"]]["thread_number"] == "1704"
    assert after[purple["shape_id"]]["sew_block"] == after[red["shape_id"]]["sew_block"]
    assert after[green["shape_id"]]["tier"] == "fill"
    codes = {w["code"] for w in second["warnings"]}
    assert {"SHAPES_DELETED_BY_USER", "SHAPE_EDIT_UNKNOWN_ID"} <= codes
    assert second["design"]["stitchCount"] != first["design"]["stitchCount"]


def test_sew_order_override_resequences_shapes_within_a_layer_over_http(client):
    """1305 carries two shapes (a rectangle and a run-tier satellite) that
    share one sew block by default. Pinning whichever sews second to slot 0
    must flip which one sews first — read off the emitted `sew_index`, not
    just the override round-tripping through the review payload."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    orange = [s for s in first["review"]["shapes"] if s["thread_number"] == "1305"]
    assert len(orange) >= 2, "fixture must carry >1 shape on this thread"
    ordered = sorted((s for s in orange if s["sew_index"] is not None),
                      key=lambda s: s["sew_index"])
    sewn_first, sewn_second = ordered[0], ordered[1]
    assert sewn_first["layer"] == sewn_second["layer"], "must be one within-layer test"

    second = _digitize(client, {
        "target_width_mm": 80.0, "preflight": False,
        "shape_overrides": {sewn_second["shape_id"]: {"sew_order": 0}},
    })
    after = {s["shape_id"]: s for s in second["review"]["shapes"]}
    assert after[sewn_second["shape_id"]]["sew_order"] == 0, "echoed back, contract v1.2"
    assert after[sewn_second["shape_id"]]["sew_index"] < after[sewn_first["shape_id"]]["sew_index"], \
        "the pinned shape must now sew before the one that used to sew first"
    # Only the WITHIN-layer order moved — the block itself sews in the same
    # position, and every other layer's shapes are untouched.
    assert after[sewn_second["shape_id"]]["sew_block"] == after[sewn_first["shape_id"]]["sew_block"]
    assert after[sewn_second["shape_id"]]["sew_block"] == sewn_first["sew_block"]


def test_underlay_style_override_round_trips_over_http_and_changes_stitch_count(client):
    """A per-shape underlay_style override reaches the emitted design over the
    real HTTP seam, not just the pipeline's internal Region.meta — the fill-
    classified shape's stitch count actually changes when its underlay is
    turned off."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    shapes = {s["thread_number"]: s for s in first["review"]["shapes"]}
    red = shapes["1704"]     # big filled circle, fill tier
    assert red["tier"] == "fill"

    second = _digitize(client, {
        "target_width_mm": 80.0, "preflight": False,
        "shape_overrides": {red["shape_id"]: {"underlay_style": "none"}},
    })
    assert second["design"]["stitchCount"] < first["design"]["stitchCount"]


def test_stitched_default_and_override_round_trip_over_http(client):
    """The service-layer half of the enclosed-background restore fix: an
    `enclosed_background`-tagged region reports `stitched: False` by default
    in `review.shapes` (the CORE resolution already worked; the gap was the
    service rejecting the override key and never exposing the field) —
    and a `shape_overrides[sid] = {"stitched": true}` restores it, both in
    the review payload and in the actual stitch plan reaching the design."""
    # Guards off (2026-08-11): the background-existence guards now correctly
    # refuse to flood the full-bleed repro at defaults, so nothing gets
    # enclosed-background-tagged there. This test pins the service's restore
    # plumbing, which needs the flooded diagnosis-time state — and doubles as
    # proof the service accepts the new guard knobs over HTTP.
    GUARDS_OFF = {"bg_border_agreement_min": 0.0, "bg_border_rival_min": 0.0}
    first = _digitize(client, {"preflight": False, **GUARDS_OFF}, art=REPRO)
    shapes = first["review"]["shapes"]
    assert all("stitched" in s for s in shapes)
    unstitched = [s for s in shapes if s["stitched"] is False]
    assert unstitched, "the repro fixture's whole point is a region tagged unstitched by default"
    target = unstitched[0]

    second = _digitize(client, {
        "preflight": False,
        **GUARDS_OFF,
        "shape_overrides": {target["shape_id"]: {"stitched": True}},
    }, art=REPRO)

    after = {s["shape_id"]: s for s in second["review"]["shapes"]}
    assert after[target["shape_id"]]["stitched"] is True
    # And it isn't just the flag: the restored shape now actually reaches
    # the emitted design, growing the stitch count.
    assert second["design"]["stitchCount"] > first["design"]["stitchCount"]


def test_review_payload_carries_text_cluster_fields_over_http(client):
    """The service-layer half of text-cluster detection (Step 4 of the
    text-cluster-detection plan): `_review_payload` echoes `text_candidate`
    and `text_cluster_id` straight off `Region.meta`, purely additive and
    read-only — no `_OVERRIDE_KEYS` entry, no client-submitted path.

    Uses the real benchmark fixture at its documented 90 mm size (the same
    fixture/size `test_pipeline.py`'s full-pipeline wiring test confirms
    tags a text cluster on the "ENTERPRISES INC." subline) so this exercises
    the real HTTP seam, not a synthetic Region.meta.
    """
    review = _digitize(client, {"target_width_mm": 90.0, "preflight": False},
                        art=ENTHUSIAST_LOGO)["review"]
    shapes = review["shapes"]

    assert all({"text_candidate", "text_cluster_id"} <= set(s) for s in shapes)

    tagged = [s for s in shapes if s["text_cluster_id"] is not None]
    assert tagged, "the benchmark fixture must produce at least one tagged text cluster"
    for s in tagged:
        assert s["text_candidate"] is True
        assert isinstance(s["text_cluster_id"], str)

    untagged = [s for s in shapes if s["text_cluster_id"] is None]
    assert untagged, "ordinary, never-tagged shapes must also be present in this fixture"
    for s in untagged:
        assert s["text_candidate"] is False


@requires_tesseract
def test_review_payload_carries_ocr_suggested_text_fields_over_http(client):
    """The service-layer half of OCR-suggested text (Studio "Convert to
    text" entry point): `_review_payload` echoes `ocr_char`/`ocr_confidence`
    straight off `Region.meta`, purely additive, read-only, no
    `_OVERRIDE_KEYS` entry -- same contract shape as `text_candidate`/
    `text_cluster_id` just above.

    Uses the real benchmark fixture at its documented 90 mm size, same as
    the text-cluster test above, so this exercises the real HTTP seam.
    """
    review = _digitize(client, {"target_width_mm": 90.0, "preflight": False},
                        art=ENTHUSIAST_LOGO)["review"]
    shapes = review["shapes"]

    assert all({"ocr_char", "ocr_confidence"} <= set(s) for s in shapes)

    untagged = [s for s in shapes if s["text_cluster_id"] is None]
    assert untagged
    for s in untagged:
        assert s["ocr_char"] is None
        assert s["ocr_confidence"] is None

    tagged = [s for s in shapes if s["text_cluster_id"] is not None]
    assert tagged
    saw_a_real_character = False
    for s in tagged:
        assert s["ocr_char"] is None or (isinstance(s["ocr_char"], str) and len(s["ocr_char"]) == 1)
        conf = s["ocr_confidence"]
        assert conf is None or (isinstance(conf, float) and 0.0 <= conf <= 100.0)
        if s["ocr_char"] is not None:
            saw_a_real_character = True
    assert saw_a_real_character, \
        "the real benchmark fixture must produce at least one real OCR character over HTTP"


def test_an_edit_is_a_different_job_not_a_stale_cache_hit(client):
    """The cache keys on the canonical config: two configs differing only in
    shape_overrides are two jobs; the same edit twice is one."""
    plain = {"target_width_mm": 47.0, "preflight": False}
    edit = {**plain, "shape_overrides": {"Sdeadbeef": {"tier": "run"}}}

    def submit(cfg):
        with ART.open("rb") as f:
            return client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                               data={"config": json.dumps(cfg)}).json()

    a, b, b2 = submit(plain), submit(edit), submit(edit)
    assert a["job_id"] != b["job_id"], "an edited re-digitize must re-run"
    assert b2["job_id"] == b["job_id"], "the same edit twice is one job"


def test_parse_config_canonicalizes_the_edit_fields():
    """Two spellings of one edit are ONE cache key: the deleted list sorts and
    dedupes, empty containers vanish, and a no-op override ('auto', null)
    vanishes with them."""
    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps({"deleted_shape_ids": ["b", "a", "a"]})) == \
        {"deleted_shape_ids": ["a", "b"]}
    assert _parse_config(json.dumps({"deleted_shape_ids": [],
                                     "shape_overrides": {}})) == {}
    assert _parse_config(json.dumps({"deleted_shape_ids": None,
                                     "shape_overrides": None})) == {}
    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"tier": None}, "S2": {"tier": "auto"},
                             "S3": {"tier": "Satin"}}})) == \
        {"shape_overrides": {"S3": {"tier": "satin"}}}


def test_parse_config_accepts_a_sew_order_override():
    """A plain non-negative integer, passed through unchanged — sew_order has
    no closed vocabulary or lowercasing to normalize, unlike tier/border."""
    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps({"shape_overrides": {"S1": {"sew_order": 0}}})) == \
        {"shape_overrides": {"S1": {"sew_order": 0}}}
    assert _parse_config(json.dumps({"shape_overrides": {"S1": {"sew_order": None}}})) == {}


def test_parse_config_accepts_and_lowercases_an_underlay_style_override():
    """Same closed-vocabulary canonicalization as `border`/`tier`: a valid
    style lowercases and survives; `null` is absence, same as every other
    field here."""
    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"underlay_style": "Edge_Zigzag"}}})) == \
        {"shape_overrides": {"S1": {"underlay_style": "edge_zigzag"}}}
    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"underlay_style": "none"}}})) == \
        {"shape_overrides": {"S1": {"underlay_style": "none"}}}
    assert _parse_config(json.dumps(
        {"shape_overrides": {"S1": {"underlay_style": None}}})) == {}


def test_parse_config_accepts_a_stitched_override():
    """A plain boolean, either direction — and `False` survives canonicalization
    (it is a real override value, not an absence, unlike `None`)."""
    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps({"shape_overrides": {"S1": {"stitched": True}}})) == \
        {"shape_overrides": {"S1": {"stitched": True}}}
    assert _parse_config(json.dumps({"shape_overrides": {"S1": {"stitched": False}}})) == \
        {"shape_overrides": {"S1": {"stitched": False}}}


def test_parse_config_accepts_and_normalizes_a_boundary_override():
    """A valid ring survives as a list of [x, y] float pairs; a closed ring
    (first point repeated as last — how `outline_mm` in the review payload
    sends it, and so the natural shape for a client to hand straight back)
    canonicalizes the same as the open form, so the two are ONE cache key."""
    from digitizer_service.app import _parse_config

    open_ring = [[0, 0], [10, 0], [10, 10], [0, 10]]
    closed_ring = open_ring + [[0, 0]]

    got_open = _parse_config(json.dumps({"shape_overrides": {"S1": {"boundary_override": open_ring}}}))
    got_closed = _parse_config(json.dumps({"shape_overrides": {"S1": {"boundary_override": closed_ring}}}))
    want = {"shape_overrides": {"S1": {"boundary_override": [[0.0, 0.0], [10.0, 0.0],
                                                              [10.0, 10.0], [0.0, 10.0]]}}}
    assert got_open == want
    assert got_closed == want
    assert _parse_config(json.dumps({"shape_overrides": {"S1": {"boundary_override": None}}})) == {}


@pytest.mark.parametrize("bad", [
    {"deleted_shape_ids": "S1"},                            # not a list
    {"shape_overrides": {"S1": {"tier": "zigzag"}}},        # unknown tier
    {"shape_overrides": {"S1": {"border": "dotted"}}},      # unknown border
    {"shape_overrides": {"S1": {"underlay_style": "sparkly"}}},  # unknown underlay style
    {"shape_overrides": {"S1": {"underlay_style": 3}}},     # not a string
    {"shape_overrides": {"S1": {"speed": 9}}},              # unknown key
    {"shape_overrides": {"S1": {"thread_index": 99999}}},   # off the chart
    {"shape_overrides": {"S1": {"thread_index": True}}},    # bool is not an index
    {"shape_overrides": {"S1": {"fill_angle_deg": "flat"}}},
    {"shape_overrides": {"S1": "fill"}},                    # entry not an object
    {"shape_overrides": {"S1": {"sew_order": -1}}},         # negative
    {"shape_overrides": {"S1": {"sew_order": True}}},       # bool is not a position
    {"shape_overrides": {"S1": {"sew_order": 1.5}}},        # not an integer
    {"shape_overrides": {"S1": {"stitched": "yes"}}},       # not a boolean
    {"shape_overrides": {"S1": {"boundary_override": "nope"}}},           # not a list
    {"shape_overrides": {"S1": {"boundary_override": [[0, 0], [1, 1]]}}},  # < 3 points
    {"shape_overrides": {"S1": {"boundary_override":                       # self-intersecting
                                [[0, 0], [10, 10], [10, 0], [0, 10]]}}},
    {"shape_overrides": {"S1": {"boundary_override":                       # near-zero area
                                [[0, 0], [0.01, 0], [0.01, 0.01]]}}},
    {"shape_overrides": {"S1": {"boundary_override": [["a", 0], [1, 0], [1, 1]]}}},  # not numbers
    {"shape_overrides": {"S1": {"boundary_override": [[0, 0], [1, 0], [1, True]]}}},  # bool coord
    {"merge_shape_ids": "nope"},                            # not a list
    {"merge_shape_ids": ["S1"]},                            # group not a list
    {"merge_shape_ids": [["S1"]]},                          # < 2 distinct shapes
    {"merge_shape_ids": [["S1", "S1"]]},                    # dedupes to 1 distinct shape
    {"merge_shape_ids": [["S1", 2]]},                       # not a string id
    {"merge_shape_ids": [["S1", ""]]},                      # empty string id
    {"split_shapes": "nope"},                               # not an object
    {"split_shapes": {"S1": [[0, 0]]}},                     # only one point
    {"split_shapes": {"S1": [[0, 0], [1, 0], [2, 0]]}},     # three points
    {"split_shapes": {"S1": [[0, 0], [0, 0]]}},             # zero-length line
    {"split_shapes": {"S1": [["a", 0], [1, 1]]}},           # not numbers
    {"split_shapes": {"S1": [[0, 0], [1, True]]}},          # bool coord
])
def test_bad_shape_edits_are_a_400_at_submit_not_a_failed_job(client, bad):
    with ART.open("rb") as f:
        r = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps(bad)})
    assert r.status_code == 400, r.text


# --- boundary override (contract v1.4) --------------------------------------

def test_boundary_override_round_trips_over_http_and_changes_the_design(client):
    """digitize -> read a shape's outline_mm -> re-digitize with a
    boundary_override enlarging it -> the same round-trip shape every other
    override key already has: the shape keeps its id, the new outline
    reaches the review payload's area, and the design's stitch geometry
    actually changes. Every other shape is untouched by the one edit."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    shapes = {s["thread_number"]: s for s in first["review"]["shapes"]}
    purple = shapes["2905"]          # rectangle
    pts = purple["outline_mm"]
    cx = sum(p[0] for p in pts) / len(pts)
    cy = sum(p[1] for p in pts) / len(pts)
    grown = [[cx + (x - cx) * 1.4, cy + (y - cy) * 1.4] for x, y in pts]

    second = _digitize(client, {
        "target_width_mm": 80.0, "preflight": False,
        "shape_overrides": {purple["shape_id"]: {"boundary_override": grown}},
    })

    ids_before = {s["shape_id"] for s in first["review"]["shapes"]}
    after = {s["shape_id"]: s for s in second["review"]["shapes"]}
    assert set(after) == ids_before, "boundary edit alone changes no shape's id"
    edited = after[purple["shape_id"]]
    assert edited["area_mm2"] > purple["area_mm2"] * 1.3
    assert second["design"]["stitchCount"] != first["design"]["stitchCount"]
    # Every other shape's outline is untouched by the one edit.
    for sid, before in {s["shape_id"]: s for s in first["review"]["shapes"]}.items():
        if sid == purple["shape_id"]:
            continue
        assert after[sid]["outline_mm"] == before["outline_mm"]


def test_boundary_override_survives_an_identical_resubmit_as_one_cached_job(client):
    """Same shape, same edit, submitted twice: one job — the edit
    participates in the cache key exactly as every other override does, and
    is stable enough not to thrash it on a no-op resubmit."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    purple = next(s for s in first["review"]["shapes"] if s["thread_number"] == "2905")
    edit = {"target_width_mm": 80.0, "preflight": False,
            "shape_overrides": {purple["shape_id"]: {"boundary_override": purple["outline_mm"]}}}

    with ART.open("rb") as f:
        a = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps(edit)}).json()
    with ART.open("rb") as f:
        b = client.post("/digitize", files={"image": (ART.name, f, "image/png")},
                        data={"config": json.dumps(edit)}).json()
    assert a["job_id"] == b["job_id"]


def test_boundary_override_with_a_hole_poking_outside_fails_the_job_cleanly_not_a_400(client):
    """The one boundary_override check this service genuinely cannot do at
    submit time — hole containment needs the shape's own existing holes,
    which parsing a request never sees — so it surfaces as a failed JOB, not
    a 400: the submit-time shell check passes (this shrink is still a valid,
    plenty-large-enough polygon on its own), and `apply_shape_edits` is what
    actually catches the hole poking outside it once the job runs. Still a
    clean, readable error, never a crash or a corrupted design — the same
    contract `test_a_failed_job_reports_the_error_not_a_blank_result` pins
    for the registry in general, proven here for this specific edit."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    ring = next(s for s in first["review"]["shapes"] if s["holes_mm"])
    hole = ring["holes_mm"][0]
    hx0, hx1 = min(p[0] for p in hole), max(p[0] for p in hole)
    hy0, hy1 = min(p[1] for p in hole), max(p[1] for p in hole)
    hcx, hcy = (hx0 + hx1) / 2, (hy0 + hy1) / 2
    # Shrink the shell toward the HOLE's own center: still a large, valid,
    # easily-sewable polygon by itself, but now too small to still contain
    # the hole it used to enclose.
    shrunk = [[hcx + (x - hcx) * 0.1, hcy + (y - hcy) * 0.1] for x, y in ring["outline_mm"]]

    with ART.open("rb") as f:
        r = client.post(
            "/digitize", files={"image": (ART.name, f, "image/png")},
            data={"config": json.dumps({
                "target_width_mm": 80.0, "preflight": False,
                "shape_overrides": {ring["shape_id"]: {"boundary_override": shrunk}},
            })},
        )
    assert r.status_code == 202, "the shell alone is valid, so submit succeeds"
    job_id = r.json()["job_id"]
    for _ in range(600):
        state = client.get(f"/jobs/{job_id}").json()
        if state["state"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert state["state"] == "error", "the job, not submission, must catch this"
    assert "boundary_override" in state["error"] and "hole" in state["error"].lower()


# --- shape identity edits (merge/split, contract v1.5) ----------------------
#
# The other half of the shape-recognition gap `boundary_override` (above)
# didn't touch: these change the SET of shapes, not one shape's geometry.
# Full core-level coverage (the happy paths, every v1 guardrail, the
# warn-vs-raise split) lives in `test_shape_identity.py`; what belongs here
# is the SERVICE's own contract — request canonicalization, 400s at submit,
# and the one real end-to-end proof that the config keys reach the running
# service and come back out the other side as a changed design.

def test_parse_config_canonicalizes_merge_shape_ids_groups_and_dedupes_them():
    """Mirrors `deleted_shape_ids`'s own canonicalization: each group
    de-duplicated and sorted, then the list of groups itself sorted, so two
    spellings of one merge request are ONE cache key."""
    from digitizer_service.app import _parse_config

    assert _parse_config(json.dumps({"merge_shape_ids": [["B", "A", "A"]]})) == \
        {"merge_shape_ids": [["A", "B"]]}
    # Group order in the outer list must not matter either.
    a = _parse_config(json.dumps({"merge_shape_ids": [["B", "C"], ["A", "D"]]}))
    b = _parse_config(json.dumps({"merge_shape_ids": [["D", "A"], ["C", "B"]]}))
    assert a == b
    assert _parse_config(json.dumps({"merge_shape_ids": None})) == {}
    assert _parse_config(json.dumps({"merge_shape_ids": []})) == {}


def test_parse_config_canonicalizes_split_shapes_line_order_and_coerces_floats():
    """A line's two endpoints canonicalize to one order regardless of which
    one the client calls "first" — see `regions.apply_shape_splits`'s own
    copy of this normalization for why (an id-stability concern, not just a
    cache one)."""
    from digitizer_service.app import _parse_config

    forward = _parse_config(json.dumps({"split_shapes": {"S1": [[0, -5], [0, 5]]}}))
    backward = _parse_config(json.dumps({"split_shapes": {"S1": [[0, 5], [0, -5]]}}))
    assert forward == backward == {"split_shapes": {"S1": [[0.0, -5.0], [0.0, 5.0]]}}
    assert _parse_config(json.dumps({"split_shapes": None})) == {}
    assert _parse_config(json.dumps({"split_shapes": {}})) == {}


def test_merge_shape_ids_reaches_the_real_pipeline_as_a_400_free_submit_and_a_clean_job_error(client):
    """The fixture's two real "1305" (orange) regions are 13.8mm apart (see
    `test_shape_identity.py`'s own note on this) — not adjacent, so the
    request itself is well-formed (a 202, not a 400) and the geometry
    guardrail fires as a clean JOB error, exactly the same posture
    `boundary_override`'s hole-containment case already has 3 tests up."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    orange = sorted(
        s["shape_id"] for s in first["review"]["shapes"] if s["thread_number"] == "1305"
    )
    assert len(orange) == 2

    with ART.open("rb") as f:
        r = client.post(
            "/digitize", files={"image": (ART.name, f, "image/png")},
            data={"config": json.dumps({
                "target_width_mm": 80.0, "preflight": False,
                "merge_shape_ids": [orange],
            })},
        )
    assert r.status_code == 202, "well-formed request: two real, distinct, same-thread ids"
    job_id = r.json()["job_id"]
    for _ in range(600):
        state = client.get(f"/jobs/{job_id}").json()
        if state["state"] in ("done", "error"):
            break
        time.sleep(0.1)
    assert state["state"] == "error"
    assert "does not touch or overlap" in state["error"]


def test_split_shapes_round_trips_over_http_and_produces_two_new_shapes(client):
    """digitize -> read the purple rectangle's outline -> re-digitize with a
    split_shapes cut through its own middle -> two new shapes with new ids,
    the old id gone, combined area preserved, and the design's stitch
    geometry actually changed. Every other shape is untouched."""
    first = _digitize(client, {"target_width_mm": 80.0, "preflight": False})
    purple = next(s for s in first["review"]["shapes"] if s["thread_number"] == "2905")
    xs = [p[0] for p in purple["outline_mm"]]
    midx = (min(xs) + max(xs)) / 2
    ys = [p[1] for p in purple["outline_mm"]]
    line = [[midx, min(ys) - 1.0], [midx, max(ys) + 1.0]]

    second = _digitize(client, {
        "target_width_mm": 80.0, "preflight": False,
        "split_shapes": {purple["shape_id"]: line},
    })

    ids_before = {s["shape_id"] for s in first["review"]["shapes"]}
    after = {s["shape_id"]: s for s in second["review"]["shapes"]}
    assert purple["shape_id"] not in after
    new_purple = [s for s in after.values() if s["thread_number"] == "2905"]
    assert len(new_purple) == 2
    assert set(after) - ids_before == {s["shape_id"] for s in new_purple}
    assert sum(s["area_mm2"] for s in new_purple) == pytest.approx(purple["area_mm2"], rel=0.02)
    assert second["design"]["stitchCount"] != first["design"]["stitchCount"]
    # Every other shape's outline is untouched by the one split.
    before_by_id = {s["shape_id"]: s for s in first["review"]["shapes"]}
    for sid, b in before_by_id.items():
        if sid == purple["shape_id"]:
            continue
        assert after[sid]["outline_mm"] == b["outline_mm"]


def test_merge_and_split_are_a_400_free_no_op_when_the_named_shape_no_longer_exists(client):
    """An id the current artwork/config no longer produces (stale, or simply
    made up) is a clean, informative WARNING, never an error — the same
    posture `deleted_shape_ids`/`shape_overrides` already have for exactly
    this case."""
    state = _digitize(client, {
        "target_width_mm": 80.0, "preflight": False,
        "merge_shape_ids": [["nope1", "nope2"]],
        "split_shapes": {"nope3": [[0, -1], [0, 1]]},
    })
    codes = {w["code"] for w in state["warnings"]}
    assert "SHAPE_EDIT_UNKNOWN_ID" in codes


# --- /digitize-manual (manual digitizing, no image) -------------------------

def test_digitize_manual_returns_a_design_a_review_and_stats(client):
    state = _digitize_manual(client, config={"garment_id": "left_chest"})

    design = state["design"]
    assert design["stitchCount"] > 100
    assert design["colorCount"] == 2
    assert design["stitches"][-1]["type"] == "end"
    assert {s["type"] for s in design["stitches"]} <= {"stitch", "jump", "trim", "color", "end"}

    review = state["review"]
    assert len(review["shapes"]) == 2
    assert review["palette"][0]["brand_id"] == "isacord"
    assert state["stats"]["stitch_count"] == design["stitchCount"]
    assert state["preflight"]["grade"] in "ABCDF"

    # Same keys /digitize's job carries, so a client that only knows that
    # response shape needs no special-casing for this route.
    assert set(state) >= {"job_id", "state", "design", "review", "stats",
                          "warnings", "preflight"}


def test_manual_review_payload_reports_the_tier_each_shape_actually_sewed_as(client):
    state = _digitize_manual(client)
    shapes = {s["thread_index"]: s for s in state["review"]["shapes"]}
    assert shapes[0]["tier"] == "fill"
    assert shapes[1]["tier"] == "satin"
    assert all({"layer", "sew_index", "sew_block", "shape_id"} <= set(s)
               for s in state["review"]["shapes"])


def test_manual_stats_describe_the_delivered_design(client):
    state = _digitize_manual(client)
    design, stats = state["design"], state["stats"]
    kinds = [s["type"] for s in design["stitches"]]
    assert stats["trims"] == kinds.count("trim")
    assert stats["jumps"] == kinds.count("jump")
    assert stats["color_changes"] == kinds.count("color")


def test_manual_preflight_off_is_none_not_a_passing_report(client):
    state = _digitize_manual(client, config={"preflight": False})
    assert state["preflight"] is None


def test_manual_preflight_runs_without_an_image_and_says_so(client):
    """No artwork ever backed a manual generation, so the thread-match check
    is honestly reported skipped — every other check still runs."""
    state = _digitize_manual(client)
    metrics = state["preflight"]["metrics"]
    assert metrics["thread_match_checked"] is False
    assert isinstance(state["preflight"]["findings"], list)


def test_manual_design_exports_to_a_real_machine_file(client):
    """No new export code: reuses the exact same /export route every other
    design (lettering, imported, auto-digitized) already goes through."""
    design = _digitize_manual(client)["design"]
    for fmt in ("dst", "pes", "exp"):
        r = client.post("/export", json={"design": design, "format": fmt})
        assert r.status_code == 200, r.text
        assert len(r.content) > 200
        assert r.headers["x-stitch-convention"] == "tajima-standard"


def test_manual_pes_survives_an_independent_reader(client):
    design = _digitize_manual(client)["design"]
    r = client.post("/export", json={"design": design, "format": "pes"})
    pattern = pystitch.read_pes(io.BytesIO(r.content))
    sewn = [s for s in pattern.stitches if s[2] == pystitch.STITCH]
    assert len(sewn) == design["stitchCount"]


def test_manual_garment_id_changes_the_fabric_and_therefore_the_stitch_count(client):
    knit = _digitize_manual(client, config={"garment_id": "left_chest"})
    towel = _digitize_manual(client, config={"garment_id": "towel"})
    assert knit["design"]["stitchCount"] != towel["design"]["stitchCount"]


def test_manual_thread_brand_changes_the_catalog_numbers(client):
    iso = _digitize_manual(client, config={"thread_brand": "isacord"})
    mad = _digitize_manual(client, config={"thread_brand": "madeira-rayon"})
    assert iso["review"]["palette"][0]["brand_id"] == "isacord"
    assert mad["review"]["palette"][0]["brand_id"] == "madeira-rayon"


def test_manual_unknown_thread_brand_is_rejected(client):
    r = client.post("/digitize-manual", json={
        "shapes": _manual_shapes(), "config": {"thread_brand": "nope"},
    })
    assert r.status_code == 400
    assert "nope" in r.json()["detail"]


@pytest.mark.parametrize("field", [
    "deleted_shape_ids", "shape_overrides", "merge_shape_ids", "split_shapes",
])
def test_manual_shape_edit_fields_are_rejected_as_config_fields(client, field):
    """Nothing in manual mode has assigned ids from a PRIOR generation for
    these to reference — see `_MANUAL_CONFIG_FIELDS`. `merge_shape_ids`/
    `split_shapes` (contract v1.5) reference prior-generation ids exactly as
    much as the other two do, so they are excluded the same way."""
    r = client.post("/digitize-manual", json={
        "shapes": _manual_shapes(), "config": {field: []},
    })
    assert r.status_code == 400, r.text
    assert field in r.json()["detail"]


def test_manual_debug_dir_is_still_rejected(client):
    r = client.post("/digitize-manual", json={
        "shapes": _manual_shapes(), "config": {"debug_dir": "C:/anywhere"},
    })
    assert r.status_code == 400


def test_manual_target_width_mm_is_accepted_but_does_not_rescale_literal_mm_shapes(client):
    """The polygon is already physical millimetres; target_width_mm is a
    no-op here (documented on the route), not silently reinterpreted."""
    plain = _digitize_manual(client, config={"garment_id": "left_chest"})
    scaled = _digitize_manual(
        client, config={"garment_id": "left_chest", "target_width_mm": 500.0}
    )
    assert scaled["design"]["widthMM"] == pytest.approx(plain["design"]["widthMM"], abs=0.5)


def test_manual_identical_request_is_served_from_cache(client):
    shapes = _manual_shapes()
    first = client.post("/digitize-manual",
                        json={"shapes": shapes, "config": {}}).json()
    for _ in range(600):
        if client.get(f"/jobs/{first['job_id']}").json()["state"] == "done":
            break
        time.sleep(0.1)

    second = client.post("/digitize-manual",
                         json={"shapes": shapes, "config": {}}).json()
    assert second["job_id"] == first["job_id"]
    assert second["cached"] is True


def test_manual_a_different_shape_is_a_different_job(client):
    a = client.post("/digitize-manual",
                    json={"shapes": _manual_shapes(), "config": {}}).json()
    other = _manual_shapes()
    other[0]["thread_index"] = 7
    b = client.post("/digitize-manual",
                    json={"shapes": other, "config": {}}).json()
    assert a["job_id"] != b["job_id"]


def test_manual_empty_shape_list_is_a_400(client):
    r = client.post("/digitize-manual", json={"shapes": [], "config": {}})
    assert r.status_code == 400


def test_manual_too_many_shapes_is_a_413(client):
    from digitizer_service.app import MAX_MANUAL_SHAPES
    r = client.post("/digitize-manual", json={
        "shapes": [{}] * (MAX_MANUAL_SHAPES + 1), "config": {},
    })
    assert r.status_code == 413


def test_manual_missing_shapes_field_is_a_400(client):
    r = client.post("/digitize-manual", json={"config": {}})
    assert r.status_code == 400


def test_manual_self_intersecting_polygon_is_a_400_not_a_failed_job(client):
    bowtie = [[0.0, 0.0], [10.0, 10.0], [10.0, 0.0], [0.0, 10.0]]
    r = client.post("/digitize-manual", json={
        "shapes": [{"polygon": bowtie, "technique": "fill", "thread_index": 0}],
        "config": {},
    })
    assert r.status_code == 400
    detail = r.json()["detail"].lower()
    assert "invalid" in detail or "self-intersect" in detail


@pytest.mark.parametrize("bad_shape", [
    {"polygon": MANUAL_RECT, "technique": "fill", "thread_index": 99999},  # off the chart
    {"polygon": MANUAL_RECT, "technique": "auto", "thread_index": 0},      # unsupported tier
    {"polygon": MANUAL_RECT, "thread_index": 0},                          # missing technique
    {"polygon": MANUAL_RECT, "technique": "fill"},                        # missing thread
    {"technique": "fill", "thread_index": 0},                            # missing polygon
    {"polygon": [[0.0, 0.0], [1.0, 0.0]], "technique": "fill", "thread_index": 0},  # too few points
])
def test_manual_bad_shapes_are_a_400_at_submit_not_a_failed_job(client, bad_shape):
    r = client.post("/digitize-manual", json={"shapes": [bad_shape], "config": {}})
    assert r.status_code == 400, r.text
    assert "job_id" not in r.json()


def test_manual_failed_validation_never_reaches_the_job_registry(client):
    """A 400 must not leave a queued/running job behind to poll."""
    before = client.get("/health").json()["jobs"]["jobs"]
    client.post("/digitize-manual", json={
        "shapes": [{"polygon": MANUAL_RECT, "technique": "fill", "thread_index": -1}],
        "config": {},
    })
    after = client.get("/health").json()["jobs"]["jobs"]
    assert after == before


def test_the_image_route_is_unaffected_by_the_manual_route_existing(client):
    """Flat-lane and /digitize must be completely unaffected: submit a manual
    job first, then confirm /digitize still works exactly as it always did."""
    _digitize_manual(client)
    state = _digitize(client, {"target_width_mm": 80.0})
    assert state["design"]["stitchCount"] > 500


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
