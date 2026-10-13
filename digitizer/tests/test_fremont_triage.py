"""Kent's 2026-10-13 Hotel Fremont stitch-out at 81 mm on a hat, pinned.

He digitized the transparent-background logo in the Studio at 81 x 44 mm,
garment Hat, 5x7 hoop, and the Studio showed 15,129 stitches in 3 colours
with "1895 completely dropped out". `tools/fremont_triage.py` replays the
request the Studio sends through the service's own steps; these tests pin
that the replay IS that request and that it reproduces his job, and pin the
1895 reading on main, so a change that moves it has to say so.

Measurement only: Fremont is an UNREPRESENTATIVE fixture -- reproduce
defects on it, never size a constant on it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from tools import fremont_triage as ft

APP = Path(__file__).resolve().parents[2] / "app" / "src"


def _js_default(name: str) -> str:
    src = (APP / "lib" / "project.js").read_text(encoding="utf-8")
    block = src[src.index("export const DEFAULT_DIGITIZE_PARAMS = {"):]
    block = block[:block.index("\n};")]
    m = re.search(rf"^\s*{name}:\s*([^,\n]+),", block, re.M)
    assert m, f"DEFAULT_DIGITIZE_PARAMS has no {name}"
    return m.group(1).strip()


def test_request_is_what_the_studio_sends():
    """Every key of `studio_request` traces to the Studio source, so a
    change to the Studio's defaults breaks this replay loudly."""
    req = ft.studio_request()
    assert req["target_width_mm"] == 81.0
    assert _js_default("max_colors") == str(req["max_colors"])
    assert _js_default("satin") == "true" and req["satin"] is True
    assert _js_default("detail_layer") == "false" and req["detail_layer"] is False
    assert _js_default("edge_cap") == json.dumps(req["edge_cap"])
    assert _js_default("border") == "null" and "border" not in req
    assert _js_default("fill_angle_deg") == "null" and "fill_angle_deg" not in req
    client = (APP / "lib" / "digitizer.js").read_text(encoding="utf-8")
    assert "cfg.detect_photographic = true;" in client and req["detect_photographic"]
    assert "cfg.faces_route_flat = true;" in client and req["faces_route_flat"]
    pills = (APP / "lib" / "garmentPills.js").read_text(encoding="utf-8")
    assert '{ id: "hat_front", short: "Hat" }' in pills and req["garment_id"] == "hat_front"
    project = (APP / "lib" / "project.js").read_text(encoding="utf-8")
    assert f"fabricRgb: {json.dumps(ft.STUDIO_FABRIC_RGB)}" in project


def test_service_accepts_the_request_unchanged():
    from digitizer_service.app import _parse_config
    assert _parse_config(json.dumps(ft.studio_request())) == ft.studio_request()


def test_fixture_is_the_transparent_upload():
    import cv2
    img = cv2.imread(str(ft.FIXTURE), cv2.IMREAD_UNCHANGED)
    assert img.shape == (1345, 2500, 4)
    assert 0.30 < float((img[..., 3] == 0).mean()) < 0.45


@pytest.fixture(scope="module")
def main_run():
    return ft.run_arm("main", preflight=False)


def test_reproduces_kents_job(main_run):
    s = main_run["plan"].stats
    colours = len({tuple(b.rgb) for b in main_run["plan"].blocks})
    assert colours == ft.KENT_COLOURS
    assert abs(s.stitch_count - ft.KENT_STITCHES) / ft.KENT_STITCHES < 0.03, s.stitch_count
    assert len(main_run["result"].regions) == 161      # his "Edit shapes (161)"
    assert abs(s.size_mm[0] - 81.0) < 1.5 and abs(s.size_mm[1] - 44.0) < 1.5


def test_1895_on_main_is_the_reported_loss(main_run):
    """PINS THE DEFECT, not a goal. At 81 mm every 1895 digit is a shape
    under `min_detail_mm`^2 (2.25 mm^2), so stage 7's small-shape rescue
    routes it to the run tier before the Column lane is asked: the digits
    sew as bean outlines of solid blobs (the 8's and 9's counters are gone
    by stage 4), and one digit sews nothing. That is Kent's "098". The
    thread still lands on most of the ink -- a run outline over a 0.2 mm
    stroke covers it -- which is why ARTWORK_UNCOVERED is silent. A change
    that fixes 1895 breaks this test on purpose: update it and say so."""
    r = ft.roi_census(main_run)["1895"]
    shapes = [s for s in r["shapes"] if min(s["rgb"]) < ft.WHITE_MIN]
    assert len(shapes) == 4
    assert all(s["under_min_detail_mm2"] for s in shapes)
    assert not any(s["column_lane"] for s in shapes)
    assert not any(s["holes"] for s in shapes)
    tiers = sorted(s["tier"] for s in shapes)
    assert tiers == ["UNSEWN", "run", "run", "run"], tiers
    assert 3.0 < r["ink_mm2"] < 5.0
    assert r["ink_bare_mm2"] < 1.5

    # `cfg.small_glyph_keep` (built OFF, 2026-10-13) is the cure, and the
    # flip is Kent's: ON, the "1" is sewn (the white ground still has no
    # hole for it, so stage 5 sews its artwork over the ground rather than
    # clipping it to nothing) and the 8 and 9 keep their counters (2 and 1,
    # 0.30-0.52 mm²).
    on = ft.roi_census(ft.run_arm("small_glyph_keep", preflight=False))["1895"]
    on_shapes = sorted((s for s in on["shapes"] if min(s["rgb"]) < ft.WHITE_MIN),
                       key=lambda s: s["shape_id"])
    assert len(on_shapes) == 4
    assert all(s["tier"] == "run" for s in on_shapes), [s["tier"] for s in on_shapes]
    assert sorted(s["holes"] for s in on_shapes) == [0, 0, 1, 2]
