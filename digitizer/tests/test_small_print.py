"""Small print (`cfg.small_print_floor`, 2026-10-12, default OFF).

Measured with `tools/small_print.py` on the Column lane at 2.5-12 mm caps:
the worst small-lettering defect at 3-4 mm is the COUNTER sewn shut -- by
stage 4's 0.56 mm2 sliver floor before the letter is tagged, by the thread
of the counter's own columns, and by link hops sewn across the counter.
These pin:

- OFF is byte-identical: the three flat-lane goldens' stitch streams (md5
  of the golden file, as `test_thread_profile.py` pins them) with the flag
  explicitly off; the Column lane's construction with `counter_clear_mm` 0
  is the call without it, run for run.
- the pieces: a dropped counter is punched back only when one laid thread
  wide (and 60 wt keeps one 40 wt drops); a penetration is held half a
  laid width off a counter and never takes a cross under the floor; a
  ring letter's counter stays more open under thread.
- the done-test: the synthetic word at a 3 mm cap through `digitize()`,
  OFF against ON, read by `tools/small_print.py` against the source line
  traced at 100 mm (`testdata/small_print_synthetic_ref.json`): more
  counter area open and fewer counters shut ON.

Every number the flag sets is a candidate (ROADMAP gate 1), on the
hairline sew-out card.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig, machine, stitches  # noqa: E402
from digitizer_core.columns import (_clear_counters, lettering_columns_shape,  # noqa: E402
                                    small_print_counters)
from digitizer_core.pipeline import digitize  # noqa: E402
from tools import small_print  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


# --- OFF is byte-identical ----------------------------------------------------

GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


def test_flag_is_off_by_default():
    assert PipelineConfig().small_print_floor is False


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
def test_off_is_byte_identical_to_the_golden(fixture):
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            small_print_floor=False))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]


def _ring(outer_r=1.3, counter_r=0.45):
    return Point(0, 0).buffer(outer_r, 64).difference(Point(0, 0).buffer(counter_r, 64))


def _stream(runs):
    return [[round(x, 6), round(y, 6), r.kind, r.jump, r.trim] for r in runs for x, y in r.points]


def test_zero_clearance_is_the_call_without_it():
    kw = dict(trim_at_mm=3.0, pull_mm=0.3, pull_floor_mm=1.5)
    for letter in (_ring(), _ring(2.0, 0.8)):
        a, ra = lettering_columns_shape(letter, "S1", **kw)
        b, rb = lettering_columns_shape(letter, "S1", counter_clear_mm=0.0, **kw)
        assert _stream(a) == _stream(b) and ra == rb


# --- the pieces -----------------------------------------------------------------

def _square(cx, cy, half):
    return [(cx - half, cy - half), (cx + half, cy - half), (cx + half, cy + half), (cx - half, cy + half)]


def test_a_dropped_counter_comes_back_only_when_one_thread_wide():
    letter = Polygon(_square(0, 0, 1.5))
    wide = _square(-0.7, 0, 0.21)       # 0.42 mm across
    narrow = _square(0.7, 0, 0.17)      # 0.34 mm across
    p40 = machine.thread_profile(40).counter_min_width_mm
    p60 = machine.thread_profile(60).counter_min_width_mm
    assert p40 == pytest.approx(0.40) and p60 == pytest.approx(0.32)
    out40 = small_print_counters(letter, [wide, narrow], p40)
    out60 = small_print_counters(letter, [wide, narrow], p60)
    assert len(out40.interiors) == 1            # 40 wt: the 0.34 mm counter stays sewn
    assert len(out60.interiors) == 2            # 60 wt keeps it: a finer thread, a finer floor
    assert small_print_counters(letter, [], p40) is letter
    assert small_print_counters(letter, None, p40) is letter
    # a ring outside the letter is never cut into it
    assert small_print_counters(letter, [_square(5, 5, 0.3)], p40) is letter


def test_a_penetration_is_held_half_a_thread_off_the_counter():
    letter = Polygon(_square(0, 0, 2.0), [_square(0, 0, 0.5)])
    # a cross whose inner end lands 0.05 mm inside the counter's edge
    a, b = [(0.45, 0.0)], [(1.9, 0.0)]
    na, nb = _clear_counters(a, b, letter, 0.2, machine.SATIN_MIN_CROSS_MM)
    assert nb == b
    assert na[0][0] == pytest.approx(0.7, abs=1e-6)     # counter edge 0.5 + 0.2
    # never under the cross floor: a short cross is held only as far as it can be
    a, b = [(0.55, 0.0)], [(1.1, 0.0)]
    na, _ = _clear_counters(a, b, letter, 0.2, machine.SATIN_MIN_CROSS_MM)
    assert na[0][0] < 0.7
    assert math.dist(na[0], b[0]) == pytest.approx(machine.SATIN_MIN_CROSS_MM)
    # a cross clear of every counter is untouched
    a, b = [(1.0, 1.0)], [(1.9, 1.0)]
    assert _clear_counters(a, b, letter, 0.2, machine.SATIN_MIN_CROSS_MM) == (a, b)


def _open_share(runs, counter: Polygon, thread_mm=0.4, ppm=40) -> float:
    x0, y0, x1, y1 = counter.bounds
    pad = 2.0
    W, H = int((x1 - x0 + 2 * pad) * ppm), int((y1 - y0 + 2 * pad) * ppm)

    def px(p):
        return (int(round((p[0] - x0 + pad) * ppm)), int(round((p[1] - y0 + pad) * ppm)))

    hole = np.zeros((H, W), np.uint8)
    cv2.fillPoly(hole, [np.array([px(p) for p in counter.exterior.coords], np.int32)], 1)
    sewn = np.zeros((H, W), np.uint8)
    prev = None
    for r in runs:
        if prev is not None and not r.jump:
            cv2.line(sewn, px(prev), px(r.points[0]), 1, int(round(thread_mm * ppm)))
        for a, b in zip(r.points, r.points[1:]):
            cv2.line(sewn, px(a), px(b), 1, int(round(thread_mm * ppm)))
        prev = r.points[-1]
    return float((hole & (1 - sewn)).sum()) / float(hole.sum())


def test_a_small_ring_letter_keeps_more_of_its_counter_open():
    """An O at a ~2.6 mm cap: a 0.9 mm counter, 0.85 mm strokes, pique's
    0.3 mm pull. ON, the thread's edge is held to the counter's edge."""
    letter = _ring(1.3, 0.45)
    counter = Polygon(letter.interiors[0])
    kw = dict(trim_at_mm=3.0, pull_mm=0.3, pull_floor_mm=1.5)
    off, _ = lettering_columns_shape(letter, "S1", **kw)
    on, rep = lettering_columns_shape(letter, "S1", counter_clear_mm=0.2, **kw)
    assert any(r.kind == stitches.SATIN for r in on) and not rep["empty"]
    o_off, o_on = _open_share(off, counter), _open_share(on, counter)
    assert o_on >= o_off + 0.15, (o_off, o_on)


# --- the done-test: the synthetic word at a 3 mm cap ---------------------------

def test_counters_open_on_the_synthetic_word_at_three_millimetres():
    ref = json.loads((TESTDATA / "small_print_synthetic_ref.json").read_text())
    image = small_print.synthetic_text()
    width = round(3.0 / ref["cap"], 2)
    off, (r_off, _p, _a) = small_print.measure(image, PipelineConfig(target_width_mm=width), ref)
    on, (r_on, _p, _a) = small_print.measure(
        image, PipelineConfig(target_width_mm=width, small_print_floor=True), ref)
    assert off["cap_mm"] == pytest.approx(3.0, abs=0.05)
    # the defect, measured 2026-10-12 (Windows): 8 of 10 counters shut,
    # 0.31 of the counter area open OFF; 4 shut, 0.68 open ON
    assert on["counter_open"] >= off["counter_open"] + 0.15, (off["counter_open"], on["counter_open"])
    assert on["counters_shut"] < off["counters_shut"]
    # stage 4 recorded the counters its floor dropped, ON only, and left
    # every polygon as the floor made it
    assert not any("small_counters" in r.meta for r in r_off.regions)
    assert any(r.meta.get("small_counters") for r in r_on.regions)
    assert (sorted(r.polygon.wkt for r in r_off.regions)
            == sorted(r.polygon.wkt for r in r_on.regions))
    # not paid for in letters: the ink still sewn
    assert on["covered"] >= off["covered"] - 0.03
