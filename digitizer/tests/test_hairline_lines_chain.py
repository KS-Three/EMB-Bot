"""Chaining the line route's strands (`cfg.hairline_lines_chain`, default OFF,
2026-10-13; `stage6_hairline_lines.strand_blocks`, `stage7_sequence`).

The line route (#882) sews every strand as its own run and cuts every hop
past `trim_at_mm`: +45 trims on owl_kent. With the flag on, a hop of at most
`HOP_MAX_MM` that lies over thread the fills already laid is sewn
needle-down instead. Every number is a property of the file, not of cloth
(ROADMAP gate 1); the 8 mm cap is a candidate (gate 3).
"""
from __future__ import annotations

import json
import math

import cv2
import numpy as np
import pytest
import shapely

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage6_blend import SourcePixels
from digitizer_core.stage6_hairline_lines import HOP_MAX_MM, SHAPE_ID, strand_blocks
from tests.test_hairline_lines import BASE as _BASE
from tests.test_hairline_lines import SIZE_PX, _drawn_lines, _md5
from tests.test_thread_profile import GOLDEN_MD5, TESTDATA, _coords_md5
from tools.hairline_lines_chain_trial import core
from tools.hairline_travel import measure_plan

ON = dict(hairline=True, hairline_from_lines=True)
PX_PER_MM = 8.0
# #882's eight dark strands on a mid-tone ground, framed in white so the
# segmenter sees the ground as a subject and fills it (unframed, the ground
# is the background and nothing is laid under the strands to hop over).
BASE = dict(_BASE, target_width_mm=40.0)


def _fixture(path):
    rng = np.random.default_rng(7)
    inner = np.full((SIZE_PX, SIZE_PX, 3), (150, 120, 95), np.float64)
    inner = np.clip(inner + rng.normal(0.0, 4.0, (SIZE_PX, SIZE_PX, 1)), 0, 255).astype(np.uint8)
    for pts in _drawn_lines():
        cv2.polylines(inner, [np.round(pts).astype(np.int32)], False, (40, 30, 25), 2,
                      cv2.LINE_AA)
    img = np.full((SIZE_PX + 80, SIZE_PX + 80, 3), 255, np.uint8)
    img[40:40 + SIZE_PX, 40:40 + SIZE_PX] = inner
    cv2.imwrite(str(path), cv2.cvtColor(img, cv2.COLOR_RGB2BGR))
    return path


def _sp(img) -> SourcePixels:
    h, w = img.shape[:2]
    return SourcePixels(rgb=img, px_per_mm=PX_PER_MM, origin_px=(w / 2.0, h / 2.0))


def _pair(gap_px: int):
    """Two thin dark vertical strands `gap_px` apart (8 px = 1 mm), 30 mm
    long, on a light ground."""
    img = np.full((320, 320, 3), (200, 190, 180), np.uint8)
    for x in (100, 100 + gap_px):
        cv2.line(img, (x, 40), (x, 280), (40, 35, 30), 2, cv2.LINE_AA)
    return img


def _blocks(img, hop_ok, chain=True):
    cfg = PipelineConfig(**ON, hairline_lines_chain=chain)
    return strand_blocks(_sp(img), cfg, entry=None, trim_at_mm=machine.TRIM_AT_MM,
                         allowed_threads=[0], hop_ok=hop_ok)


def _kinds(blocks):
    return [(r.kind, r.jump, r.trim) for _t, runs in blocks for r in runs]


@pytest.fixture(scope="module")
def plans(tmp_path_factory):
    src = _fixture(tmp_path_factory.mktemp("hlc") / "dark_lines.png")
    result = run_stages(src, PipelineConfig(**BASE, **ON))
    return {
        "result": result,
        "lines": plan_stitches(result, PipelineConfig(**BASE, **ON)),
        "chain": plan_stitches(result, PipelineConfig(**BASE, **ON, hairline_lines_chain=True)),
    }


def _strand_runs(plan):
    return [r for _, r in plan.iter_runs() if r.shape_id == SHAPE_ID and r.kind == stitches.RUN]


def _hairline_report(plan) -> dict:
    return next(w for w in plan.warnings if w["code"] == "HAIRLINE_TIER_SEWN")


# --- OFF is byte-identical ---------------------------------------------------

def test_the_flag_defaults_off():
    assert PipelineConfig().hairline_lines_chain is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_the_flag_alone_is_byte_identical_to_the_flat_golden(fixture):
    """#848's pins: the flag without the line route is inert."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _coords_md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _r, plan = digitize(TESTDATA / fixture,
                        PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                       hairline_lines_chain=True))
    assert _md5(plan) == GOLDEN_MD5[fixture]


def test_the_flag_changes_nothing_off_the_line_route():
    """Drawn hair (gradient lane) never reaches the line route: with the
    hairline tier and the line route both on, the chain flag is inert."""
    base = dict(target_width_mm=80.0, hairline=True)
    result = run_stages(TESTDATA / "synthetic" / "hair_strands.png", PipelineConfig(**base))
    assert result.design_class == "gradient"
    want = _md5(plan_stitches(result, PipelineConfig(**base)))
    for kw in (dict(hairline_lines_chain=True),
               dict(hairline_from_lines=True, hairline_lines_chain=True)):
        assert _md5(plan_stitches(result, PipelineConfig(**base, **kw))) == want


def test_off_the_route_is_as_before(plans):
    """Off, no hop run, no `hops` in the census, every gap a jump."""
    assert not [r for _, r in plans["lines"].iter_runs()
                if r.shape_id == SHAPE_ID and r.kind == stitches.TRAVEL]
    rep = _hairline_report(plans["lines"])
    assert "hops" not in rep and "hop_mm" not in rep


def test_chain_needs_the_line_route(plans):
    """Without `hairline_from_lines` the flag is inert, even on a photo lane."""
    cfg = PipelineConfig(**BASE, hairline=True)
    result = plans["result"]
    assert _md5(plan_stitches(result, cfg)) == _md5(
        plan_stitches(result, PipelineConfig(**BASE, hairline=True, hairline_lines_chain=True)))


# --- the chain ----------------------------------------------------------------

def test_a_covered_hop_is_sewn_needle_down():
    img = _pair(40)  # 5 mm apart: past trim_at_mm (3), under HOP_MAX_MM (8)
    off, off_rep = _blocks(img, lambda a, b: True, chain=False)
    on, on_rep = _blocks(img, lambda a, b: True)
    assert "hops" not in off_rep
    assert [k for k in _kinds(off)] == [("run", False, False), ("run", True, True)]
    assert on_rep["hops"] == 1 and 4.5 < on_rep["hop_mm"] < 5.5
    assert [k for k in _kinds(on)] == [("run", False, False), ("travel", False, False),
                                       ("run", False, False)]
    assert on_rep["strands"] == off_rep["strands"] == 2 and on_rep["jumps"] == 0
    # The strands themselves are the same, point for point.
    strands = lambda blocks: [r.points for _t, runs in blocks for r in runs  # noqa: E731
                              if r.kind == "run"]
    assert strands(on) == strands(off)
    # The hop is a walk at the fills' travel pitch, ends excluded.
    hop = next(r for _t, runs in on for r in runs if r.kind == "travel")
    prev_end = on[0][1][0].points[-1]
    nxt = on[0][1][2].points[0]
    walk = [prev_end, *hop.points, nxt]
    assert all(math.dist(p, q) <= machine.TRAVEL_STITCH_MM + 1e-9 for p, q in zip(walk, walk[1:]))


def test_a_hop_over_bare_cloth_is_cut():
    on, rep = _blocks(_pair(40), lambda a, b: False)
    assert rep["hops"] == 0 and rep["jumps"] == 1
    assert _kinds(on) == [("run", False, False), ("run", True, True)]


def test_a_hop_past_the_cap_is_cut_even_when_covered():
    gap_px = int((HOP_MAX_MM + 2.0) * PX_PER_MM)
    on, rep = _blocks(_pair(gap_px), lambda a, b: True)
    assert rep["hops"] == 0 and rep["jumps"] == 1
    assert _kinds(on)[-1] == ("run", True, True)


def test_without_the_flag_a_hop_check_is_never_asked():
    asked = []
    _blocks(_pair(40), lambda a, b: asked.append((a, b)) or True, chain=False)
    assert asked == []


def test_the_chain_cuts_the_trims_and_moves_no_strand(plans):
    lines, chain = plans["lines"], plans["chain"]
    # Same strands, in the same order, point for point.
    # (Lock stitches sit at the ends of a cut and move with it: compare inside.)
    assert [core(r.points) for r in _strand_runs(chain)] == [core(r.points) for r in _strand_runs(lines)]
    rep = _hairline_report(chain)
    assert rep["hops"] > 0
    assert rep["strands"] == _hairline_report(lines)["strands"]
    assert chain.stats.trims < lines.stats.trims
    assert lines.stats.trims - chain.stats.trims <= rep["hops"]
    # No hop is longer than the cap, and each one is a TRAVEL run between two
    # strands, entered without a jump.
    runs = [r for _, r in plan_runs(chain)]
    n = 0
    for i, r in enumerate(runs):
        if r.shape_id == SHAPE_ID and r.kind == stitches.TRAVEL:
            n += 1
            assert not runs[i + 1].jump and not runs[i + 1].trim
            assert math.dist(runs[i - 1].points[-1], runs[i + 1].points[0]) <= HOP_MAX_MM + 1e-6
    assert n > 0


def plan_runs(plan):
    return list(plan.iter_runs())


def test_every_hop_lies_over_laid_thread_and_none_over_bare_cloth(plans):
    """The corrected thread-over-bare-fabric number (#895) does not rise."""
    lines, chain = plans["lines"], plans["chain"]
    laid = shapely.STRtree([shapely.LineString(r.points) for _, r in chain.iter_runs()
                            if r.shape_id != SHAPE_ID and r.kind != stitches.TRAVEL
                            and len(r.points) >= 2])
    runs = [r for _, r in chain.iter_runs() if r.points]
    for i, r in enumerate(runs):
        if r.shape_id == SHAPE_ID and r.kind == stitches.TRAVEL:
            a, b = runs[i - 1].points[-1], runs[i + 1].points[0]
            n = max(2, int(math.dist(a, b) / 0.1))
            pts = shapely.points([(a[0] + (b[0] - a[0]) * k / n, a[1] + (b[1] - a[1]) * k / n)
                                  for k in range(n + 1)])
            hit = laid.query(pts, predicate="dwithin",
                             distance=machine.COVERAGE_THREAD_W_MM / 2.0)
            assert len(set(hit[0].tolist())) == len(pts)
    assert (measure_plan(chain, with_legacy=False)["thread_bare_mm"]
            <= measure_plan(lines, with_legacy=False)["thread_bare_mm"] + 1e-6)
