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
    # 0.31 of the counter area open OFF; 4 shut, 0.68 open ON with the
    # Column lane alone, 2 shut, 0.81 open once the fill tier holds its
    # rows off the counters too (2026-10-13)
    assert on["counter_open"] >= off["counter_open"] + 0.15, (off["counter_open"], on["counter_open"])
    assert on["counters_shut"] < off["counters_shut"]
    # the 8 and the 0 (right of the design centre by a quarter of its
    # width) lose their text tag at this size and fall to the FILL tier:
    # all four of their counters sewn solid OFF, held open ON (part 2).
    # Measured 0.63 / 0.69 (the 8) and 0.29 / 0.39 (the 0, whose slash is
    # a bar thinner than the hold and is kept: its thread still covers the
    # counters beside it).
    x_8 = 0.25 * off["width_mm"]
    fill_off = [c["open"] for c in off["per_counter"] if c["at"][0] > x_8]
    fill_on = [c["open"] for c in on["per_counter"] if c["at"][0] > x_8]
    assert len(fill_off) == len(fill_on) == 4
    assert max(fill_off) < 0.05, fill_off
    assert min(fill_on) >= 0.2 and sum(fill_on) / 4 >= 0.4, fill_on
    # stage 4 recorded the counters its floor dropped, ON only, and left
    # every polygon as the floor made it
    assert not any("small_counters" in r.meta for r in r_off.regions)
    assert any(r.meta.get("small_counters") for r in r_on.regions)
    assert (sorted(r.polygon.wkt for r in r_off.regions)
            == sorted(r.polygon.wkt for r in r_on.regions))
    # not paid for in letters: the ink still sewn
    assert on["covered"] >= off["covered"] - 0.03


# --- part 2: the run and fill tiers (2026-10-13) -------------------------------
#
# #873 kept counters open in the Column lane only. At 3-4 mm a letter is also
# sewn by the RUN tier (bean passes on its outline: golden_tee's GOLF) or the
# FILL tier (the synthetic 8 and 0, which lose their text tag at a 3 mm cap).
# Under the same flag both now sew the shape with each counter cut out of it,
# grown by half the block's laid width (`columns.small_print_clear`), so the
# ring's or the rows' thread edge meets the counter edge. Hand-built letters
# through `sequence`, so these pins are geometry, not a trace.

from digitizer_core.columns import small_print_clear  # noqa: E402
from digitizer_core.fabrics import fabric_for_garment  # noqa: E402
from digitizer_core.regions import Region  # noqa: E402
from digitizer_core.stage5_overlap import PlannedRegion  # noqa: E402
from digitizer_core.stage7_sequence import sequence  # noqa: E402

_O = Point(0, 0).buffer(1.0, 32).difference(Point(0, 0).buffer(0.45, 32))   # a kept counter
_B = Polygon([(2.1, -1.2), (3.9, -1.2), (3.9, 1.2), (2.1, 1.2)])              # two dropped,
_B_COUNTERS = [_square(3.05, 0.55, 0.3), _square(3.05, -0.55, 0.3)]           # 0.6 mm across


def _letters(tier):
    t = {"tier": tier} if tier else {}
    sc = {"small_counters": [[list(p) for p in r] for r in _B_COUNTERS]}
    # the O is tagged lettering; the B is not (a letter that lost its tag)
    # and is small print only by the counters stage 4 dropped
    return [(_O, dict(t, text_candidate=True)), (_B, dict(t, **sc))]


def _planned(letters, extra=()):
    out = []
    for i, (poly, meta) in enumerate(list(letters) + list(extra)):
        meta = dict(meta)
        reg = Region(shape_id=f"S{i}", polygon=poly, thread_index=meta.pop("thread", 0),
                     thread_number="0134", area_mm2=poly.area, source="test",
                     meta=dict({"layer": 0}, **meta))
        out.append(PlannedRegion(region=reg, polygon=poly, sew_index=i))
    return out


def _sequenced(letters, on: bool, extra=(), **kw):
    blocks, _w = sequence(_planned(letters, extra), fabric_for_garment("left_chest"),
                          PipelineConfig(small_print_floor=on, **kw))
    return [r for b in blocks for r in b.runs]


def _md5_runs(runs) -> str:
    return _md5([[round(x, 4), round(y, 4), r.kind, r.jump, r.trim] for r in runs for x, y in r.points])


# OFF stitch streams, measured on origin/main (a17d4355) before this change,
# with the flag off and on alike (main ignored it outside the Column lane):
# the run-tier pin, and the same letters through the fill tier.
TIER_OFF_MD5 = {
    "run": "cd444497637ab858cd2dacef3cb9a712",
    "fill": "604b2bb5aa2b52c18b7bd907bc80d2f1",
}


@pytest.mark.parametrize("tier", sorted(TIER_OFF_MD5))
def test_run_and_fill_tier_off_is_byte_identical(tier):
    kw = {} if tier == "run" else {"satin": False}
    runs = _sequenced(_letters("run" if tier == "run" else None), False, **kw)
    assert (stitches.RUN if tier == "run" else stitches.FILL) in {r.kind for r in runs}
    assert _md5_runs(runs) == TIER_OFF_MD5[tier]


def test_the_run_tier_keeps_more_of_a_counter_open():
    """Done-test, run tier: the O's counter ring is sewn half a laid width
    out. Measured 0.08 -> 0.65 open (the bean's chords cut the curve)."""
    counter = Polygon(_O.interiors[0])
    off = _sequenced(_letters("run"), False)
    on = _sequenced(_letters("run"), True)
    assert {r.kind for r in on} == {stitches.RUN}
    o_off, o_on = _open_share(off, counter), _open_share(on, counter)
    assert o_on >= o_off + 0.3, (o_off, o_on)


def test_the_fill_tier_opens_its_counters():
    """Done-test, fill tier (satin off, so both letters fill): the B's two
    dropped counters come back as holes, and both letters' rows stop half a
    laid width short of every counter. Measured 0.28 -> 0.99 (O) and
    0.00 -> 0.98 (B). No needle-down move crosses a counter."""
    off = _sequenced(_letters(None), False, satin=False)
    on = _sequenced(_letters(None), True, satin=False)
    assert stitches.FILL in {r.kind for r in on}
    o = Polygon(_O.interiors[0])
    b = [Polygon(r) for r in _B_COUNTERS]
    assert _open_share(on, o) >= _open_share(off, o) + 0.3
    for c in b:
        assert _open_share(off, c) < 0.05
        assert _open_share(on, c) >= 0.6
    inside = [h.buffer(-0.05) for h in (o, *b)]
    prev = None
    for r in on:
        pts = ([prev] if prev is not None and not r.jump else []) + list(r.points)
        for p, q in zip(pts, pts[1:]):
            if p != q:
                seg = LineString([p, q])
                assert not any(seg.intersects(h) for h in inside), (r.kind, p, q)
        prev = r.points[-1]


def test_a_hole_another_shape_fills_is_not_a_counter():
    """A layered letter: the O's hole is another colour's ink. Holding the
    thread off it would open a seam of bare fabric, so ON sews as OFF."""
    inner = (Point(0, 0).buffer(0.45, 32), {"thread": 1})
    letters = [(_O, {"tier": "run", "text_candidate": True})]
    assert (_md5_runs(_sequenced(letters, True, extra=[inner]))
            == _md5_runs(_sequenced(letters, False, extra=[inner])))


def test_a_bar_thinner_than_the_hold_is_kept():
    """Two counters 0.3 mm apart (a B's middle bar, a slashed zero's slash)
    and a ring 0.15 mm thick: a 0.2 mm hold from each side would eat both,
    so both stay ink. Everywhere else the counter grows by the hold."""
    letter = Polygon(_square(0, 0, 1.0))
    top = Polygon(_square(0, 0.4, 0.25))        # y 0.15..0.65
    bottom = Polygon(_square(0, -0.4, 0.25))    # y -0.65..-0.15: a 0.3 mm bar between
    out = small_print_clear(letter, [top, bottom], 0.2, art=letter)
    assert out.covers(Point(0, 0))                          # the bar survives
    assert not out.covers(Point(0.35, 0.4))                 # 0.1 off the counter: held clear
    assert out.covers(Point(0.5, 0.4))                      # 0.25 off: still sewn
    ring = Polygon(_square(0, 0, 0.65))                     # 0.15 thick round a 1 mm counter
    out = small_print_clear(ring, [Polygon(_square(0, 0, 0.5))], 0.2, art=ring)
    assert out.covers(Point(0.6, 0.0))                      # never cut through to the outside
    assert small_print_clear(letter, [], 0.2, art=letter) is letter
