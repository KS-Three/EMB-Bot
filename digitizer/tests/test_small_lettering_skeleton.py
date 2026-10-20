"""`cfg.small_lettering_skeleton` (built OFF 2026-10-13): small lettering
thinner than the thread sews as ONE run down its skeleton
(`digitizer_core/stage6_small_letter.py`), not as a bean run on its outline.

Kent's Hotel Fremont at 81 mm on a hat: the tagline and EST have strokes of
0.22-0.30 mm under a 0.40 mm thread, and the small-shape rescue sews each as
an outline 1.6-3.2x the stroke with its counters shut (PR #905). These pin the
tier on synthetic glyphs, stage 4's counter record, the stage 7 route, and
that OFF -- and ON, on the flat-lane goldens -- is byte-identical. Every
number the tier uses is a candidate (ROADMAP gate 1); `tools/
small_lettering_skeleton.py` carries the Fremont measurement and the corpus.
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import digitize, plan_stitches, run_stages
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage3_segment import RegionMask
from digitizer_core.stage4_vectorize import vectorize
from digitizer_core.stage6_small_letter import (glyph_polygon, qualifies,
                                                skeleton_letter_runs)

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"
P40 = machine.thread_profile(40)
STROKE = 0.24          # Fremont's tagline stroke, mm


def _glyph(*lines, w=STROKE):
    """A monoline glyph: each polyline buffered to a stroke `w` wide."""
    return unary_union([LineString(ln).buffer(w / 2.0, cap_style=2, join_style=2)
                        for ln in lines]).buffer(0)


def _T(h=2.2, bar=1.6):
    return _glyph([(-bar / 2, 0), (bar / 2, 0)], [(0, 0), (0, h)])


def _E(h=2.4, arm=1.4):
    return _glyph([(arm, 0), (0, 0), (0, h), (arm, h)], [(0, h / 2), (arm * 0.85, h / 2)])


def _sew(poly, floor=machine.MIN_STITCH_MM, entry=None):
    return skeleton_letter_runs(poly, "G1", max_width_mm=P40.width_mm, stitch_mm=1.5,
                                run_width_mm=P40.hairline_run_width_mm, entry=entry,
                                trim_at_mm=machine.TRIM_AT_MM, min_mm=floor)


def _steps(runs):
    return [math.dist(a, b) for r in runs for a, b in zip(r.points, r.points[1:])]


def test_flag_is_off_by_default():
    cfg = PipelineConfig()
    assert cfg.small_lettering_skeleton is False
    assert cfg.small_lettering_skeleton_floor_mm is None


# A T whose half-bar is longer than the floor (the needle can turn into it)
# at each floor: 1.0 mm needs a 3 mm letter, 0.73 mm sews Fremont's 2.2 mm.
@pytest.mark.parametrize("floor,h,bar", [(machine.MIN_STITCH_MM, 3.0, 2.4),
                                         (machine.BEAN_STITCH_MM, 2.2, 1.6)])
def test_a_thin_T_is_one_run_down_its_middle(floor, h, bar):
    runs, rep = _sew(_T(h, bar), floor=floor)
    assert not rep["empty"], rep
    assert len(runs) == 1 and rep["jumps"] == 0          # ONE run: no jump, no trim
    assert runs[0].kind == "run"
    # every stitch at or above the floor
    assert min(_steps(runs)) >= floor - 1e-9
    # the needle stays on the stroke's middle: within half a laid width of
    # the skeleton the glyph was drawn from
    spine = unary_union([LineString([(-bar / 2, 0), (bar / 2, 0)]), LineString([(0, 0), (0, h)])])
    assert max(spine.distance(Point(q)) for q in runs[0].points) <= 0.5 * P40.width_mm
    # and the three free tips are reached
    for tip in [(-bar / 2, 0), (bar / 2, 0), (0, h)]:
        assert min(math.dist(tip, q) for q in runs[0].points) <= 0.25, tip


def test_the_needle_floor_declines_a_letter_it_would_bend():
    """Fremont's 2.2 mm T at the 1.0 mm floor: a 0.8 mm half-bar is shorter
    than one stitch, so the needle would have to cut across the letter. It
    goes back to the ladder (the outline) instead."""
    runs, rep = _sew(_T(), floor=machine.MIN_STITCH_MM)
    assert runs == [] and rep["declined"] == "shape", rep


def test_an_E_keeps_its_middle_arm_where_the_hairline_drop_guard_would_lose_it():
    """The hairline tier drops a path under `RUN_MIN_LOOP_MM` (2.2 mm), so a
    small E's middle arm vanishes there; here the arm is taken out and back
    inside the one run."""
    runs, rep = _sew(_E(), floor=machine.BEAN_STITCH_MM)
    assert not rep["empty"], rep
    assert len(runs) == 1
    assert rep["retrace_mm"] > 0
    assert min(math.dist((1.4 * 0.85, 1.2), q) for q in runs[0].points) <= 0.25


def test_a_stroke_wider_than_the_thread_is_declined():
    runs, rep = _sew(_glyph([(0, 0), (0, 3)], w=0.7))
    assert runs == [] and rep["empty"] and rep["declined"] == "width"
    assert qualifies(_glyph([(0, 0), (0, 3)], w=0.7), P40.width_mm) is None


def test_a_glyph_shorter_than_one_stitch_is_declined_not_shrunk():
    runs, rep = _sew(_glyph([(0, 0), (0, 0.6)]))
    assert runs == [] and rep["empty"]


def test_a_counter_the_run_goes_round_stays_open():
    """An O, 2.4 mm across: the run goes round the counter, no chord enters
    it."""
    ring = Point(0, 0).buffer(1.2, 64).difference(Point(0, 0).buffer(1.2 - STROKE, 64))
    runs, rep = _sew(ring, floor=machine.BEAN_STITCH_MM)
    assert not rep["empty"], rep
    assert rep["counters"] == 1 and rep["counter_crossings"] == 0
    hole = Polygon(ring.interiors[0])
    core = hole.buffer(-0.25 * 2.0 * (1.2 - STROKE))
    for r in runs:
        for a, b in zip(r.points, r.points[1:]):
            assert not LineString([a, b]).intersects(core)


def test_a_counter_too_small_to_go_round_at_the_floor_is_declined():
    """A 1.4 mm O: its skeleton loop is 1.16 mm across, so every stitch at
    the 1.0 mm floor is a chord across the counter -- the glyph goes back to
    the ladder rather than shut it. (A 1.0 mm O has no stitch at all: its
    loop is narrower than the floor, `declined` "empty".)"""
    ring = Point(0, 0).buffer(0.7, 64).difference(Point(0, 0).buffer(0.7 - STROKE, 64))
    runs, rep = _sew(ring, floor=machine.MIN_STITCH_MM)
    assert runs == [] and rep["empty"]
    assert rep["declined"] in ("counter", "shape")
    small = Point(0, 0).buffer(0.5, 64).difference(Point(0, 0).buffer(0.5 - STROKE, 64))
    runs, rep = _sew(small, floor=machine.MIN_STITCH_MM)
    assert runs == [] and rep["declined"] == "empty"


def test_a_serif_hook_shorter_than_one_stitch_is_trimmed_and_a_long_one_kept():
    from digitizer_core.stage6_small_letter import trim_hooks
    arm = [(x / 100.0, 0.0) for x in range(0, 151)]           # 1.5 mm arm
    hook = [(1.5, y / 100.0) for y in range(1, 31)]             # 0.3 mm serif down
    e = {"pts": arm + hook, "a": 0, "b": -1, "closed": False, "free_a": False, "free_b": True}
    (out,), cut = trim_hooks([e], machine.BEAN_STITCH_MM)
    assert cut == pytest.approx(0.3, abs=0.02)
    assert math.dist(out["pts"][-1], (1.5, 0.0)) < 0.02
    long_leg = [(1.5, y / 100.0) for y in range(1, 101)]        # a 1.0 mm leg: an L, not a serif
    (kept,), cut = trim_hooks([{**e, "pts": arm + long_leg}], machine.BEAN_STITCH_MM)
    assert cut == 0.0 and kept["pts"][-1] == (1.5, 1.0)


# --- a glyph under two needle floors: the small-glyph floor's second try ----------

def _sew2(poly, floor=machine.MIN_STITCH_MM, small=0.5, entry=None):
    return skeleton_letter_runs(poly, "G1", max_width_mm=P40.width_mm, stitch_mm=1.5,
                                run_width_mm=P40.hairline_run_width_mm, entry=entry,
                                trim_at_mm=machine.TRIM_AT_MM, min_mm=floor,
                                small_floor_mm=small)


def _E_est():
    """Fremont's EST E at 81 mm: 1.6 mm tall, 1.1 mm arms, 0.22 mm strokes."""
    return _glyph([(1.1, 0), (0, 0), (0, 1.6), (1.1, 1.6)], [(0, 0.8), (0.935, 0.8)], w=0.22)


def test_small_floor_default_is_the_tiny_stitch():
    assert PipelineConfig().small_lettering_skeleton_small_floor_mm == machine.TINY_STITCH_MM == 0.5


def test_an_E_under_two_floors_is_declined_at_the_floor_and_taken_by_the_second_try():
    """Fremont's EST E: 1.6 mm tall, 0.22 mm strokes. The stem has no room
    for a needle point at the middle arm a floor from both ends, so the
    one-floor tier declines it; the second try sews it as one run, every
    arm reached, every stitch at or over the small floor."""
    e = _E_est()
    runs, rep = _sew2(e, small=None)
    assert runs == [] and rep["declined"] in ("shape", "empty"), rep
    assert "small_floor" not in rep
    runs, rep = _sew2(e)
    assert not rep["empty"], rep
    assert rep["small_floor"] == 1 and rep["first_declined"] in ("shape", "empty")
    assert len(runs) == 1 and rep["jumps"] == 0
    assert min(_steps(runs)) >= 0.5 - 1e-9
    spine = unary_union([LineString([(1.1, 0), (0, 0), (0, 1.6), (1.1, 1.6)]),
                         LineString([(0, 0.8), (0.935, 0.8)])])
    assert max(spine.distance(Point(q)) for q in runs[0].points) <= 0.5 * P40.width_mm
    for tip in [(1.1, 0), (1.1, 1.6), (0.935, 0.8)]:
        assert min(math.dist(tip, q) for q in runs[0].points) <= 0.25, tip


def test_a_glyph_two_floors_or_more_gets_no_second_try():
    """The tagline's 2.2 mm T, declined at the 1.0 floor, is not small enough
    for the second try: it stays the outline, as before."""
    runs, rep = _sew2(_T(), floor=machine.MIN_STITCH_MM)
    assert runs == [] and rep["declined"] == "shape", rep
    assert "small_floor" not in rep and "small_floor_declined" not in rep


def test_a_glyph_the_floor_takes_never_reaches_the_second_try():
    a, ra = _sew2(_T(3.0, 2.4), small=None)
    b, rb = _sew2(_T(3.0, 2.4))
    assert not ra["empty"] and [r.points for r in a] == [r.points for r in b] and ra == rb


def test_trim_stubs_drops_a_foot_shorter_than_the_floor_and_keeps_the_stroke():
    from digitizer_core.stage6_small_letter import trim_stubs
    stem = {"pts": [(0.0, y / 10.0) for y in range(0, 15)], "a": -1, "b": 0, "closed": False,
            "free_a": True, "free_b": False}
    foot = {"pts": [(0.0, 1.4), (0.3, 1.4)], "a": 0, "b": -2, "closed": False,
            "free_a": False, "free_b": True}
    leg = {"pts": [(0.0, 1.4), (-0.8, 1.4)], "a": 0, "b": -3, "closed": False,
           "free_a": False, "free_b": True}
    out, cut = trim_stubs([stem, foot, leg], 0.5)
    assert out == [stem, leg] and cut == pytest.approx(0.3)
    # one edge is the glyph: kept however short
    out, cut = trim_stubs([foot], 0.5)
    assert out == [foot] and cut == 0.0


def test_glyph_polygon_punches_recorded_counters_back():
    blob = _glyph([(0, 0), (0, 2)], w=1.0)
    counter = [(-0.1, 0.8), (0.1, 0.8), (0.1, 1.2), (-0.1, 1.2)]
    out = glyph_polygon(blob, [counter, [(5, 5), (6, 5), (6, 6)]])
    assert len(out.interiors) == 1
    assert out.area == pytest.approx(blob.area - 0.08, abs=1e-6)
    assert glyph_polygon(blob, None) is blob


# --- stage 4: the counter record ----------------------------------------------

def _small_a(ppm=30.0):
    """A sub-detail glyph (1.2 x 1.7 mm at 30 px/mm) with one 0.28 mm2
    counter, under stage 4's sliver floor."""
    m = np.zeros((100, 100), bool)
    m[20:71, 30:66] = True
    m[40:56, 40:56] = False
    p = Prep(rgb=np.zeros(m.shape + (3,), np.uint8), bg_mask=np.zeros(m.shape, bool),
             px_per_mm=ppm, art_bbox=(0, 0, m.shape[1], m.shape[0]))
    return m, p


@pytest.mark.parametrize("flag", [False, True])
def test_stage4_records_a_rescued_glyphs_dropped_counter_only_under_the_flag(flag):
    m, p = _small_a()
    regions, _dropped = vectorize([RegionMask.from_full(m, layer=0)], [0], p,
                                  PipelineConfig(small_lettering_skeleton=flag,
                                                 # `small_glyph_keep` (ON by default since 2026-10-13)
                                                 # keeps the counter in the polygon, so nothing is
                                                 # dropped to record; this test is about the floor.
                                                 small_glyph_keep=False))
    (r,) = regions
    assert r.meta.get("rescued_small_shape")
    assert len(r.polygon.interiors) == 0                 # the polygon is the floor's, either way
    assert bool(r.meta.get("small_counters")) is flag
    if flag:
        back = glyph_polygon(r.polygon, r.meta["small_counters"])
        assert len(back.interiors) == 1


# --- which shapes: letters of a line of text --------------------------------------

def _region(sid, poly, thread=1, **meta):
    from digitizer_core.regions import Region
    return Region(shape_id=sid, polygon=poly, thread_index=thread, thread_number=str(thread),
                  area_mm2=float(poly.area), meta=meta)


def test_text_line_members_takes_a_cluster_and_the_letters_it_missed():
    """Fremont's tagline A's are `lettering_group` only (their dropped
    counter made them blobs to the text tagger) but sit inside the line; a
    banner's row of tick marks is `lettering_group` only and sits outside
    every line, so it is not taken."""
    from shapely import affinity
    from digitizer_core.stage6_small_letter import text_line_members
    line = [_region(f"L{i}", affinity.translate(_T(), 3.0 * i, 0.0), text_candidate=True,
                    text_cluster_id="TC1", lettering_group=True) for i in (0, 2)]
    missed = _region("A", affinity.translate(_T(), 3.0, 0.0), lettering_group=True)
    other_thread = _region("B", affinity.translate(_T(), 3.0, 0.0), thread=2, lettering_group=True)
    tick = _region("TICK", affinity.translate(_T(), 30.0, 0.0), lettering_group=True)
    got = text_line_members(line + [missed, other_thread, tick])
    assert got == {"L0", "L2", "A"}


# --- stage 7: the route ----------------------------------------------------------

def _with_glyph(result, glyph, tagged=True):
    base = result.regions[0]
    meta = {"layer": base.meta["layer"], "rescued_small_shape": True}
    if tagged:
        meta.update(text_candidate=True, text_cluster_id="TC1")
    g = dataclasses.replace(base, shape_id="SGLYPH", polygon=glyph, area_mm2=float(glyph.area),
                            meta=meta)
    return dataclasses.replace(result, regions=list(result.regions) + [g])


def _glyph_runs(plan):
    return [r for _, r in plan.iter_runs() if r.shape_id == "SGLYPH" and r.points]


@pytest.fixture(scope="module")
def script_result():
    return run_stages(TESTDATA / "synthetic" / "thin_script.png",
                      PipelineConfig(target_width_mm=60.0, forced_class="flat"))


def test_stage7_sews_a_tagged_small_glyph_as_one_skeleton_run(script_result):
    from shapely import affinity
    glyph = affinity.translate(_T(), 40.0, 0.0)
    res = _with_glyph(script_result, glyph)
    base = dict(target_width_mm=60.0, forced_class="flat")
    off = _glyph_runs(plan_stitches(res, PipelineConfig(**base)))
    on = _glyph_runs(plan_stitches(res, PipelineConfig(**base, small_lettering_skeleton=True,
                                                       small_lettering_skeleton_floor_mm=0.73)))
    assert off and on
    spine = affinity.translate(unary_union([LineString([(-0.8, 0), (0.8, 0)]),
                                            LineString([(0, 0), (0, 2.2)])]), 40.0, 0.0)
    off_d = [spine.distance(Point(q)) for r in off for q in r.points]
    on_d = [spine.distance(Point(q)) for r in on for q in r.points]
    # OFF traces the outline (a half stroke off the middle); ON rides it
    assert np.median(off_d) >= 0.5 * STROKE - 0.02
    assert max(on_d) <= 0.5 * P40.width_mm
    assert sum(len(r.points) for r in on) < sum(len(r.points) for r in off)


def test_stage7_sews_an_EST_sized_glyph_at_the_default_floor(script_result):
    """Flag ON, floor and small floor at their defaults: a 1.6 mm E (Fremont's
    EST) rides its skeleton instead of the outline; with the second try off
    (`small_lettering_skeleton_small_floor_mm` None) it is the outline, as
    #913 left it."""
    from shapely import affinity
    glyph = affinity.translate(_E_est(), 40.0, 0.0)
    res = _with_glyph(script_result, glyph)
    base = dict(target_width_mm=60.0, forced_class="flat")
    off = _glyph_runs(plan_stitches(res, PipelineConfig(**base)))
    one = _glyph_runs(plan_stitches(res, PipelineConfig(**base, small_lettering_skeleton=True,
                                                        small_lettering_skeleton_small_floor_mm=None)))
    on = _glyph_runs(plan_stitches(res, PipelineConfig(**base, small_lettering_skeleton=True)))
    assert [r.points for r in one] == [r.points for r in off]
    spine = affinity.translate(unary_union([LineString([(1.1, 0), (0, 0), (0, 1.6), (1.1, 1.6)]),
                                            LineString([(0, 0.8), (0.935, 0.8)])]), 40.0, 0.0)
    assert on and max(spine.distance(Point(q)) for r in on for q in r.points) <= 0.5 * P40.width_mm
    assert sum(len(r.points) for r in on) < sum(len(r.points) for r in off)


def test_stage7_leaves_an_untagged_small_shape_on_the_outline(script_result):
    from shapely import affinity
    glyph = affinity.translate(_T(), 40.0, 0.0)
    res = _with_glyph(script_result, glyph, tagged=False)
    base = dict(target_width_mm=60.0, forced_class="flat")
    off = _glyph_runs(plan_stitches(res, PipelineConfig(**base)))
    on = _glyph_runs(plan_stitches(res, PipelineConfig(**base, small_lettering_skeleton=True)))
    assert [r.points for r in on] == [r.points for r in off]


# --- OFF (and ON, here) is byte-identical ----------------------------------------

# The flat-lane goldens' stitch streams, as `test_small_print.py` pins them.
GOLDEN_MD5 = {
    "logo_alpha.png": "50b666027292342f490cb50758a7fcde",
    "logo_whitebg.png": "e1e001f4b23de052d9102a8acbce26d9",
    "ribbon_curve.png": "f31c29f2d98d63ce919d762beb6da58a",
}


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("flag", [False, True])
def test_goldens_are_byte_identical_either_way(fixture, flag):
    """OFF is the engine as it was. ON too, on these three: none has a
    lettering shape the small-shape rescue sends to the run tier."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none",
                                            small_lettering_skeleton=flag))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
