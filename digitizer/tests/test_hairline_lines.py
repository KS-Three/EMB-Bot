"""Hairline strands from LINES (`cfg.hairline_from_lines`, default OFF,
2026-10-13; `stage6_hairline_lines`).

On a raster lane the segmenter merges fine strands into regions, so the
region tier never sees them (#876, docs/hairline-photo-trial-2026-10-12.md).
The line route takes them from FDoG lines instead and sews them as runs over
the untouched fills. Every number is a property of the file, not of cloth
(ROADMAP gate 1).
"""
from __future__ import annotations

import json
import math

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, Point

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_hairline_lines import LINE_CLASSES, SHAPE_ID, applies, extract_strands
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5

N_LINES = 8
PX_PER_MM = 8.0
SIZE_PX = 240


def _drawn_lines():
    """Eight gently curved, non-crossing strands (px polylines)."""
    out = []
    for i in range(N_LINES):
        x0 = 30 + i * 25
        t = np.linspace(0.0, 1.0, 50)
        out.append(np.column_stack([x0 + 6 * np.sin(2.5 * t + i), 30 + 180 * t]))
    return out


def _fixture(path):
    """Thin dark lines (2 px = 0.25 mm at 30 mm wide) over a mid-tone ground
    with a little noise: what a fine dark hair over skin or fur looks like
    to the photo lane."""
    rng = np.random.default_rng(7)
    img = np.full((SIZE_PX, SIZE_PX, 3), (150, 120, 95), np.float64)
    img += rng.normal(0.0, 4.0, (SIZE_PX, SIZE_PX, 1))
    img = np.clip(img, 0, 255).astype(np.uint8)
    for pts in _drawn_lines():
        cv2.polylines(img, [np.round(pts).astype(np.int32)], False, (40, 30, 25), 2,
                      cv2.LINE_AA)
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return path


# `photo_scene`: the photo lane without `auto_photo_tier`'s streamline route
# (photo_subject only), so OFF carries no raster and the plan is quick.
BASE = dict(target_width_mm=30.0, forced_class="photo_scene", photo_prep=False)


@pytest.fixture(scope="module")
def plans(tmp_path_factory):
    src = _fixture(tmp_path_factory.mktemp("hl") / "dark_lines.png")
    off_cfg = PipelineConfig(**BASE)
    on_cfg = PipelineConfig(**BASE, hairline=True)
    lines_cfg = PipelineConfig(**BASE, hairline=True, hairline_from_lines=True)
    off_result = run_stages(src, off_cfg)
    lines_result = run_stages(src, lines_cfg)
    return {
        "off_result": off_result,
        "lines_result": lines_result,
        "off": plan_stitches(off_result, off_cfg),
        "flag_alone": plan_stitches(off_result, PipelineConfig(**BASE, hairline_from_lines=True)),
        "on": plan_stitches(off_result, on_cfg),
        "lines": plan_stitches(lines_result, lines_cfg),
    }


def _md5(plan) -> str:
    return _coords_md5([[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
                        for _, r in plan.iter_runs() for x, y in r.points])


def _sewn(plan) -> dict:
    w = [x for x in plan.warnings if x["code"] == "HAIRLINE_TIER_SEWN"]
    return w[0] if w else {"strands": 0, "dropped": 0}


# --- OFF is byte-identical ---------------------------------------------------

@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_alone_is_byte_identical_to_the_flat_golden(fixture):
    """#848's pins: `hairline_from_lines` without `hairline` is inert."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       hairline_from_lines=True))
    assert _md5(plan) == GOLDEN_MD5[fixture]


def test_the_flag_alone_changes_nothing_on_the_photo_lane(plans):
    assert plans["off_result"].design_class == "photo_scene"
    assert _md5(plans["flag_alone"]) == _md5(plans["off"])
    # Off, no raster is carried for it (on, `run_stages` carries one).
    assert plans["off_result"].source_pixels is None
    assert plans["lines_result"].source_pixels is not None


def test_the_line_route_leaves_drawn_hair_to_the_region_tier():
    """Drawn hair classifies `gradient`; its strands ARE shapes, which the
    region tier sews. The line route stays out: photo lanes only."""
    cfg = PipelineConfig(hairline=True, hairline_from_lines=True)
    assert not applies(cfg, "flat") and not applies(cfg, "gradient")
    assert set(LINE_CLASSES) == {"photo_subject", "photo_scene"}
    assert all(applies(cfg, c) for c in LINE_CLASSES)
    assert not applies(PipelineConfig(hairline_from_lines=True), "photo_subject")
    on_cfg = PipelineConfig(target_width_mm=80.0, hairline=True)
    result = run_stages(TESTDATA / "synthetic" / "hair_strands.png", on_cfg)
    assert result.design_class == "gradient"
    both = plan_stitches(result, PipelineConfig(target_width_mm=80.0, hairline=True,
                                                hairline_from_lines=True))
    assert _md5(both) == _md5(plan_stitches(result, on_cfg))


# --- the done-test: lines sew strands the regions do not --------------------

def test_lines_sew_the_strands_the_region_tier_misses(plans):
    on, lines = _sewn(plans["on"]), _sewn(plans["lines"])
    assert lines.get("source") == "lines"
    # Every drawn strand is sewn (fragments allowed: at least N - 2 runs).
    assert lines["strands"] >= N_LINES - 2
    assert lines["strands"] > on["strands"]
    runs = [r for _, r in plans["lines"].iter_runs() if r.shape_id == SHAPE_ID]
    assert len(runs) == lines["strands"]
    assert all(r.kind == "run" for r in runs)
    steps = [math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:])
             if not math.isclose(math.dist(a, b), machine.TIE_STITCH_MM, abs_tol=1e-6)]
    assert min(steps) >= machine.MIN_STITCH_MM - 1e-6
    assert np.median(steps) == pytest.approx(1.5, abs=0.3)
    # On the drawn lines: every needle point within a thread width of one.
    sp = plans["lines_result"].source_pixels
    drawn = [LineString([sp.to_mm(x, y) for x, y in pts]) for pts in _drawn_lines()]
    for r in runs:
        for x, y in r.points:
            assert min(d.distance(Point(x, y)) for d in drawn) < 0.4
    # The drawn length is covered: the strands' thread is at least 70% of it.
    sewn = sum(math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:]))
    assert sewn >= 0.7 * sum(d.length for d in drawn)


def test_the_strands_sew_last_over_the_untouched_fills(plans):
    off, lines = plans["off"], plans["lines"]
    # Nothing carved: every block before the strands is OFF's, stitch for stitch.
    n = len(off.blocks)
    assert [_md5_block(b) for b in lines.blocks[:n]] == [_md5_block(b) for b in off.blocks]
    tail = lines.blocks[n:]
    assert tail and all(r.shape_id == SHAPE_ID for b in tail for r in b.runs)
    # In the design's own thread (no new spool): the darkest one, for dark lines.
    used = {b.thread_index for b in off.blocks}
    assert {b.thread_index for b in tail} <= used


def _md5_block(b) -> str:
    return _coords_md5([[round(x, 4), round(y, 4)] for r in b.runs for x, y in r.points])


# --- the ridge test ----------------------------------------------------------

def _sp(img) -> SourcePixels:
    h, w = img.shape[:2]
    return SourcePixels(rgb=img, px_per_mm=PX_PER_MM, origin_px=(w / 2.0, h / 2.0))


def test_a_step_edge_is_not_a_strand_and_both_polarities_are_read():
    """Left half dark, right half light: the edge between is NOT a strand.
    A thin light line on the dark half and a thin dark line on the light
    half are, each in its own polarity."""
    img = np.zeros((SIZE_PX, SIZE_PX, 3), np.uint8)
    img[:, : SIZE_PX // 2] = (60, 50, 45)
    img[:, SIZE_PX // 2:] = (200, 190, 180)
    cv2.line(img, (60, 30), (60, 210), (215, 210, 205), 2, cv2.LINE_AA)    # light
    cv2.line(img, (180, 30), (180, 210), (35, 30, 25), 2, cv2.LINE_AA)     # dark
    strands, census = extract_strands(_sp(img), PipelineConfig(hairline=True,
                                                               hairline_from_lines=True))
    long = [s for s in strands if s["length_mm"] >= machine.RUN_MIN_LOOP_MM]
    by = {p: [s for s in long if s["polarity"] == p] for p in ("dark", "light")}
    assert len(by["dark"]) == 1 and len(by["light"]) == 1
    sp = _sp(img)
    for s, x_px in ((by["dark"][0], 180), (by["light"][0], 60)):
        xs = [sp.to_px(x, y)[0] for x, y in s["pts"]]
        assert all(abs(x - x_px) < 2.0 for x in xs)
    # The edge at x = 120 px was found by the detector and refused.
    assert sum(census["refused_no_ridge"].values()) >= 1
    for s in strands:
        assert all(abs(sp.to_px(x, y)[0] - SIZE_PX / 2) > 2.0 for x, y in s["pts"])
