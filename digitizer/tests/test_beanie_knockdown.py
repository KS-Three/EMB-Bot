"""Beanie knockdown (`cfg.beanie_knockdown`, built OFF; `knockdown.py`).

Rule R9 of `docs/pro-digitizer-rules-2026-10-21.md`: on every beanie in the
professional's zip the first colour block is a sparse tatami (0.5 mm rows, no
underlay) over the whole design grown ~1.5 mm, in the garment's colour. These
pin the construction, the colour choice, that it only ever touches a beanie,
and that OFF is the engine byte for byte.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace

import numpy as np
import pytest
from shapely.geometry import LineString, MultiPoint, Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, digitize, knockdown, stitches
from digitizer_core.stitches import StitchBlock, StitchRun
from digitizer_core.threads import CHART, rgb_to_lab
from tests.conftest import TESTDATA

KHAKI = (208, 166, 96)          # the pro's "Khaki" cone on the Becker beanie PES


def _md5(plan) -> str:
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def _cfg(**kw):
    return PipelineConfig(garment_id="beanie", garment_rgb=KHAKI, **kw)


# --- construction -----------------------------------------------------------------

def test_flag_is_off_by_default():
    assert PipelineConfig().beanie_knockdown is False


def test_only_a_beanie_gets_one():
    assert knockdown.applies(_cfg(beanie_knockdown=True))
    assert not knockdown.applies(_cfg())
    for g in ("hat_front", "left_chest", None):
        assert not knockdown.applies(replace(_cfg(beanie_knockdown=True), garment_id=g))


def test_outline_grows_by_the_margin_bridges_near_gaps_and_fills_holes():
    ring = box(0, 0, 10, 10).difference(box(3, 3, 7, 7))      # a letter O
    near = box(12, 0, 14, 10)                                    # 2 mm away
    far = box(40, 0, 45, 5)                                      # its own piece
    pieces = knockdown.outline([ring, near, far])
    assert len(pieces) == 2
    big = pieces[0]
    assert all(len(p.interiors) == 0 for p in pieces)
    assert big.contains(Point(5, 5))                             # the counter is covered
    x0, y0, x1, y1 = big.bounds
    assert x0 == pytest.approx(-knockdown.MARGIN_MM, abs=0.06)
    assert x1 == pytest.approx(14 + knockdown.MARGIN_MM, abs=0.06)
    assert big.contains(Point(11, 5))                            # the 2 mm gap is bridged


def test_an_island_inside_a_wide_counter_is_not_a_second_piece():
    frame = box(0, 0, 40, 40).difference(box(5, 5, 35, 35))    # 30 mm counter
    dot = box(18, 18, 22, 22)                                    # far from the frame
    pieces = knockdown.outline([frame, dot])
    assert len(pieces) == 1 and pieces[0].contains(Point(20, 20))


def test_block_is_sparse_rows_no_underlay_in_the_garment_cone():
    block, rep = knockdown.knockdown_block([box(0, 0, 30, 12)], _cfg(beanie_knockdown=True), 3.0)
    assert rep["applied"] and rep["pieces"] == 1
    want = CHART.nearest_index(rgb_to_lab(np.array([KHAKI], dtype=float))[0])
    assert block.thread_index == want
    kinds = {r.kind for r in block.runs}
    assert stitches.UNDERLAY not in kinds and stitches.FILL in kinds
    assert not any(r.trim for r in block.runs)                   # one piece, one thread
    # rows: the fill's row-to-row steps sit at the knockdown pitch
    pts = [p for r in block.runs if r.kind == stitches.FILL for p in r.points]
    steps = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    assert max(steps) <= knockdown.STITCH_MM + 1e-6
    # the footprint reaches the margin and no further
    hull = MultiPoint(pts).convex_hull
    assert hull.bounds[0] == pytest.approx(-knockdown.MARGIN_MM, abs=0.3)
    assert hull.bounds[2] == pytest.approx(30 + knockdown.MARGIN_MM, abs=0.3)


def test_row_pitch_is_the_knockdowns():
    block, _ = knockdown.knockdown_block([box(0, 0, 40, 20)], _cfg(beanie_knockdown=True), 3.0)
    pts = np.array([p for r in block.runs if r.kind == stitches.FILL for p in r.points])
    # rows are parallel lines; project onto the normal of the longest stitch direction
    d = np.diff(pts, axis=0)
    long = d[np.hypot(d[:, 0], d[:, 1]) > 2.0]
    ang = math.atan2(np.median(np.sin(2 * np.arctan2(long[:, 1], long[:, 0]))),
                     np.median(np.cos(2 * np.arctan2(long[:, 1], long[:, 0])))) / 2
    v = np.sort(-pts[:, 0] * math.sin(ang) + pts[:, 1] * math.cos(ang))
    rows = [v[0]]
    for x in v[1:]:
        if x - rows[-1] > 0.1:
            rows.append(x)
    assert np.median(np.diff(rows)) == pytest.approx(knockdown.ROW_MM, abs=0.02)


def test_no_garment_colour_no_knockdown():
    block, rep = knockdown.knockdown_block([box(0, 0, 10, 10)],
                                           replace(_cfg(beanie_knockdown=True), garment_rgb=None), 3.0)
    assert block is None and rep["reason"] == "no garment colour"


def _blk(thread, n=1):
    return StitchBlock(thread_index=thread, thread_number=CHART[thread].number,
                       rgb=CHART[thread].rgb,
                       runs=[StitchRun(points=[(0.0, 0.0), (1.0, 0.0)]) for _ in range(n)])


def test_prepend_is_its_own_block_unless_the_first_is_the_same_cone():
    kd = _blk(5)
    out = knockdown.prepend([_blk(7), _blk(9)], kd)
    assert [b.thread_index for b in out] == [5, 7, 9] and out[0] is kd
    head = _blk(5, n=2)
    out = knockdown.prepend([head, _blk(9)], kd)
    assert [b.thread_index for b in out] == [5, 9]
    assert len(out[0].runs) == 3 and out[0].runs[1].trim and out[0].runs[1].jump


# --- through the pipeline ------------------------------------------------------------

FIXTURE = "logo_alpha.png"
#: `logo_alpha.png` at 60 mm on a khaki beanie, flag OFF: the plan before this
#: flag existed (captured from `git archive 2e873933`, module absent, under
#: conftest's OPENCV_IPP=avx2). HAT_MD5 is the same art on a hat_front.
BEANIE_OFF_MD5 = "f3cdf273aa9e21adbddef7ddbd52bd2b"
HAT_MD5 = "19a77b6b5ad43ff5528f4ddd590cfeb0"


@pytest.fixture(scope="module")
def runs():
    out = {}
    for name, kw in {"off": {}, "on": {"beanie_knockdown": True}}.items():
        out[name] = digitize(TESTDATA / FIXTURE, _cfg(target_width_mm=60.0, **kw))[1]
    return out


def test_on_prepends_one_block_and_leaves_the_design_alone(runs):
    off, on = runs["off"], runs["on"]
    assert len(on.blocks) == len(off.blocks) + 1
    kd = on.blocks[0]
    assert {r.shape_id for r in kd.runs} == {knockdown.SHAPE_ID}
    tail = [[(r.points, r.kind, r.jump, r.trim) for r in b.runs] for b in on.blocks[1:]]
    assert tail == [[(r.points, r.kind, r.jump, r.trim) for r in b.runs] for b in off.blocks]
    assert on.palette[1:] == off.palette


def test_on_covers_every_design_stitch(runs):
    # the sewn rows (lines, not penetrations: those are a stitch apart), each
    # widened to reach the next row
    cover = unary_union([LineString(r.points).buffer(knockdown.ROW_MM)
                         for r in runs["on"].blocks[0].runs if len(r.points) > 1])
    design = [p for _, r in runs["off"].iter_runs() for p in r.points]
    outside = [p for p in design if not cover.contains(Point(p))]
    assert len(outside) <= 0.01 * len(design)


def test_off_is_byte_identical(runs):
    assert _md5(runs["off"]) == BEANIE_OFF_MD5


def test_on_other_garments_changes_nothing():
    base = dict(target_width_mm=60.0, garment_rgb=KHAKI, garment_id="hat_front")
    off = digitize(TESTDATA / FIXTURE, PipelineConfig(**base))[1]
    on = digitize(TESTDATA / FIXTURE, PipelineConfig(beanie_knockdown=True, **base))[1]
    assert _md5(on) == _md5(off) == HAT_MD5


def test_a_lift_inside_the_knockdown_becomes_travel_along_the_edge():
    """The pro's knockdown is one needle-down piece on all six files. Stage 6
    alone lifts across a tall U's notch (its travel budget refuses the
    detour, here at rows 0 deg); `_stay_down` routes round the edge instead."""
    u = box(0, 0, 60, 8).union(box(0, 0, 8, 90)).union(box(52, 0, 60, 90))
    poly = knockdown.outline([u])[0]
    raw, _ = knockdown.stitch_shape(poly, "k", angle_deg=0.0, row_mm=knockdown.ROW_MM,
                                    stitch_mm=knockdown.STITCH_MM, underlay_style="none",
                                    trim_at_mm=3.0)
    assert sum(r.trim for r in raw) == 1
    fixed = knockdown._stay_down(raw, poly)
    assert not any(r.jump or r.trim for r in fixed)
    cover = poly.buffer(0.02)
    pts = [p for r in fixed for p in r.points]
    assert all(cover.contains(Point(p)) for p in pts)
    assert max(math.dist(a, b) for a, b in zip(pts, pts[1:])) <= knockdown.STITCH_MM + 1e-6
