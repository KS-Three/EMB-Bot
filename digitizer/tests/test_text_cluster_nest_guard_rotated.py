"""`cfg.text_cluster_nest_guard_rotated` (2026-11-07, built OFF): a rotated glyph is not
its axis-aligned box.

The text tagger drops a letter candidate whose axis-aligned bounding box sits inside a
larger candidate's (`textcluster._drop_nested`). A shape set at an angle has a box far
larger than itself, and the empty corners of that box are where the drop goes wrong: a
badge turned 30 deg holds the tagline beside it in a corner of its box, and a tall letter
on a turned baseline holds the small mark next to it.

ON: a candidate whose box holds another's must also COVER the other's polygon with a
rotated footprint before it nests it -- the box of its polygon in its run's own baseline
frame when it is a member of a run (three or more linked candidates), its minimum-area
rotated rectangle (`cv2.minAreaRect`) otherwise. Each footprint is cut to the candidate's
axis-aligned box, so ON can only KEEP a candidate OFF dropped, never drop one OFF kept.
A run or a rectangle within `NEST_ROTATED_MIN_DEG` (10) of an axis keeps the box, so a
level line is the engine as it was. The 6x-median door (`nest_guard`) is untouched; the
rescued round and the house-angle group keep today's drop. OFF: byte for byte.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import random

import pytest
from shapely import affinity
from shapely.geometry import box

from digitizer_core import PipelineConfig, digitize
from digitizer_core import textcluster as tc
from digitizer_core.regions import Region

from .conftest import FLAT_GOLDEN_MD5, TESTDATA


def _region(sid: str, poly, rescued: bool = False) -> Region:
    r = Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
               area_mm2=float(poly.area))
    if rescued:
        r.meta["rescued_small_shape"] = True
    return r


def _cand(sid: str, poly, rescued: bool = False) -> tc._Candidate:
    x0, y0, x1, y1 = poly.bounds
    return tc._Candidate(region=_region(sid, poly, rescued), height_mm=y1 - y0, width_mm=x1 - x0,
                         stroke_mean_mm=1.0, stroke_cv=0.2, cx=(x0 + x1) / 2.0, cy=(y0 + y1) / 2.0)


def _ring(w: float, h: float, t: float = 2.0):
    """A frame: an outline `t` thick, w x h, from the origin corner."""
    return box(0.0, 0.0, w, h).difference(box(t, t, w - t, h - t))


def _turn(poly, deg: float):
    return affinity.rotate(poly, deg, origin=(0.0, 0.0))


def _ids(cands) -> set[str]:
    return {c.region.shape_id for c in cands}


# --- the scenes ----------------------------------------------------------------------

def _tilted_frame_scene(deg: float = 30.0):
    """A 30 x 20 mm badge turned `deg`, and a word of four 6 mm bars on the same
    baseline sitting just below it: inside the badge's axis-aligned box (its empty
    lower-right corner), outside the badge itself."""
    badge = _turn(_ring(30.0, 20.0), deg)
    bars = [_turn(affinity.translate(box(x, 0.0, x + 1.2, 6.0), 14.0, -9.0), deg)
            for x in (2.0, 5.0, 8.0, 11.0)]
    return badge, bars


def _turned_word_scene(deg: float = 40.0):
    """Four 8 mm letters on a baseline turned `deg`, and a 2 mm mark (an apostrophe)
    just past the first stem at cap height: inside the stem's axis-aligned box,
    outside the stem's own turned box."""
    stems = [_turn(box(x, 0.0, x + 1.2, 8.0), deg) for x in (0.0, 3.0, 6.0, 9.0)]
    mark = _turn(box(1.5, 5.0, 2.3, 7.0), deg)
    return stems, mark


def test_the_scenes_are_what_they_say():
    badge, bars = _tilted_frame_scene()
    inside_box = [box(*badge.bounds).covers(b) for b in bars]
    assert inside_box[:3] == [True] * 3 and not any(badge.minimum_rotated_rectangle.covers(b) for b in bars)
    stems, mark = _turned_word_scene()
    assert box(*stems[0].bounds).covers(box(*mark.bounds))
    assert not stems[0].minimum_rotated_rectangle.covers(mark)


def test_off_a_tilted_badge_swallows_the_word_in_the_corner_of_its_box():
    badge, bars = _tilted_frame_scene()
    cands = [_cand("W", badge)] + [_cand(f"L{i}", b) for i, b in enumerate(bars)]
    assert _ids(tc._drop_nested(cands)) == {"W", "L3"}             # three of four letters gone


def test_on_the_badge_nests_with_its_own_rectangle_and_the_word_stays():
    badge, bars = _tilted_frame_scene()
    cands = [_cand("W", badge)] + [_cand(f"L{i}", b) for i, b in enumerate(bars)]
    assert _ids(tc._drop_nested(cands, rotated=True)) == {"W", "L0", "L1", "L2", "L3"}
    # independent of the 6x door: the 32 mm badge is 5.6x the bars' 5.8 mm boxes, under it
    assert _ids(tc._drop_nested(cands, nest_guard=True)) == {"W", "L3"}
    assert _ids(tc._drop_nested(cands, nest_guard=True, rotated=True)) == {"W", "L0", "L1", "L2", "L3"}


def test_on_a_run_member_nests_with_its_box_in_the_runs_frame():
    stems, mark = _turned_word_scene()
    cands = [_cand(f"T{i}", s) for i, s in enumerate(stems)] + [_cand("a", mark)]
    assert _ids(tc._drop_nested(cands)) == {"T0", "T1", "T2", "T3"}      # the mark is swallowed
    assert _ids(tc._drop_nested(cands, rotated=True)) == {"T0", "T1", "T2", "T3", "a"}
    assert abs(tc._run_angle_deg([_cand(f"T{i}", s) for i, s in enumerate(stems)]) - 40.0) < 1e-6


def test_a_level_line_is_the_engine_as_it_was():
    """The same word and mark level: the mark is beside the stem, nested neither way,
    and every footprint stands as the box (the fit is 0 deg)."""
    stems, mark = _turned_word_scene(deg=0.0)
    cands = [_cand(f"T{i}", s) for i, s in enumerate(stems)] + [_cand("a", mark)]
    assert _ids(tc._drop_nested(cands)) == _ids(tc._drop_nested(cands, rotated=True)) == {"T0", "T1", "T2", "T3", "a"}
    boxes = [c.region.polygon.bounds for c in cands]
    assert tc._rotated_footprints(cands, boxes, [False] * len(cands)) == [None] * len(cands)


def test_a_speck_inside_a_turned_glyph_still_drops():
    """The case the drop exists for: a rescued fragment riding inside a glyph's
    footprint. The glyph is turned 35 deg, alone (no run), so its footprint is its
    minimum-area rectangle, and the speck inside it is still a fragment."""
    glyph, speck = _turn(box(0.0, 0.0, 4.0, 6.0), 35.0), _turn(box(1.0, 1.0, 2.0, 2.0), 35.0)
    others = [_cand(f"L{i}", box(20.0 + 3.0 * i, 0.0, 21.0 + 3.0 * i, 6.0)) for i in range(3)]
    cands = [_cand("G", glyph), _cand("s", speck, rescued=True)] + others
    for on in (False, True):
        assert _ids(tc._drop_nested(cands, rotated=on)) == {"G", "L0", "L1", "L2"}


def test_on_only_ever_keeps_more(seed: int = 0):
    """Every footprint is cut to its own box, so an ON drop is an OFF drop: over random
    scenes of turned boxes, ON's kept set holds OFF's."""
    rng = random.Random(seed)
    for _ in range(40):
        cands = []
        for i in range(rng.randint(3, 12)):
            w, h = rng.uniform(0.5, 12.0), rng.uniform(0.5, 12.0)
            x, y = rng.uniform(-10.0, 10.0), rng.uniform(-10.0, 10.0)
            poly = affinity.rotate(box(x, y, x + w, y + h), rng.uniform(-90.0, 90.0))
            cands.append(_cand(f"C{i}", poly, rescued=rng.random() < 0.3))
        for guard in (False, True):
            off, on = _ids(tc._drop_nested(cands, guard)), _ids(tc._drop_nested(cands, guard, rotated=True))
            assert off <= on


@pytest.mark.parametrize("deg, off_axis", [(0.0, 0.0), (7.0, 7.0), (-7.0, 7.0), (40.0, 40.0),
                                           (85.0, 5.0), (-85.0, 5.0), (130.0, 40.0)])
def test_the_off_axis_angle(deg, off_axis):
    assert abs(tc._off_axis_deg(deg) - off_axis) < 1e-9


def test_the_near_axis_door():
    """A rectangle or a run within `NEST_ROTATED_MIN_DEG` of an axis keeps its box."""
    assert tc.NEST_ROTATED_MIN_DEG == 10.0
    assert tc._min_area_rect(_turn(box(0.0, 0.0, 10.0, 4.0), 6.0)) is None
    assert tc._min_area_rect(_turn(box(0.0, 0.0, 10.0, 4.0), 84.0)) is None
    rect = tc._min_area_rect(_turn(box(0.0, 0.0, 10.0, 4.0), 30.0))
    assert rect is not None and abs(rect.area - 40.0) < 0.5
    ring = tc._min_area_rect(_turn(_ring(30.0, 20.0), 30.0))                 # a frame's ink runs along its edges
    assert ring is not None and abs(ring.area - 600.0) < 1.0


def _plus(w: float = 5.2, h: float = 6.9, t: float = 0.6):
    """Window mullions: a level plus, arms `w` across and `h` down, `t` thick."""
    return box(-w / 2, -t / 2, w / 2, t / 2).union(box(-t / 2, -h / 2, t / 2, h / 2))


def test_a_plus_is_not_a_frame_and_keeps_its_box():
    """The tips of a plus are the corners of a square turned 45 deg, so its minimum-
    area rectangle is turned and smaller than its box -- and the four panes between
    its arms sit outside that rectangle. Gaulke's window mullions (5.2 x 6.9 mm) did
    exactly this on the first build, and the panes tagged as a four-letter word. A
    rectangle whose edges the ink does not run along is no frame: the box stands."""
    plus = _plus()
    (_c, (w, h), ang) = __import__("cv2").minAreaRect(tc.get_coordinates(plus).astype("float32"))
    assert tc._off_axis_deg(float(ang)) > tc.NEST_ROTATED_MIN_DEG and w * h < 0.8 * plus.envelope.area
    assert tc._min_area_rect(plus) is None
    panes = [box(sx * 0.5, sy * 0.5, sx * 2.4, sy * 3.2) for sx in (-1, 1) for sy in (-1, 1)]
    cands = [_cand("X", plus)] + [_cand(f"p{i}", p) for i, p in enumerate(panes)]
    assert _ids(tc._drop_nested(cands)) == _ids(tc._drop_nested(cands, rotated=True)) == {"X"}
    assert tc.NEST_RECT_EDGE_COVER_MIN == 0.5 and tc.NEST_RECT_EDGE_TOL == 0.05


def test_a_grid_has_no_baseline():
    """Four glyphs in a 2 x 2 grid spread equally along and across any axis: no run
    angle, so their boxes stand whatever the arithmetic would have fitted."""
    grid = [_cand(f"g{i}", box(x, y, x + 2.0, y + 3.0)) for i, (x, y) in enumerate([(0, 0), (3, 0), (0, 4), (3, 4)])]
    assert tc._run_angle_deg(grid) is None
    line = [_cand(f"l{i}", _turn(box(3.0 * i, 0.0, 3.0 * i + 1.0, 6.0), 25.0)) for i in range(3)]
    assert abs(tc._run_angle_deg(line) - 25.0) < 1e-6
    assert tc.NEST_RUN_AXIS_MIN == 2.0
    assert tc._run_angle_deg(line[:1]) is None


# --- the tagger ---------------------------------------------------------------------

def _tags(regions):
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


def _scene_regions():
    badge, bars = _tilted_frame_scene()
    return [_region("W", badge)] + [_region(f"L{i}", b) for i, b in enumerate(bars)]


@pytest.mark.parametrize("wide", [False, True])
def test_off_the_word_beside_the_tilted_badge_is_not_tagged(wide):
    regions = _scene_regions()
    tc.detect_text_clusters(regions, None, wide_letters=wide)
    assert all(v is None for v in _tags(regions).values())


@pytest.mark.parametrize("wide", [False, True])
def test_on_the_word_beside_the_tilted_badge_is_tagged(wide):
    regions = _scene_regions()
    tc.detect_text_clusters(regions, None, wide_letters=wide, nest_guard_rotated=True)
    tags = _tags(regions)
    assert tags["L0"] is not None and tags["L0"] == tags["L1"] == tags["L2"] == tags["L3"]
    assert tags["W"] is None                                    # the badge is not a letter of the line


def test_on_a_level_scene_is_unchanged():
    def scene():
        return [_region(f"B{i}", box(20.0 + 3.0 * i, 10.0, 21.0 + 3.0 * i, 16.0)) for i in range(3)]
    off, on = scene(), scene()
    tc.detect_text_clusters(off, None)
    tc.detect_text_clusters(on, None, nest_guard_rotated=True)
    assert _tags(off) == _tags(on) and _tags(on)["B0"] is not None


# --- wiring and OFF -----------------------------------------------------------------

def test_the_flag_is_off_and_the_pipeline_passes_nothing_when_off():
    assert PipelineConfig().text_cluster_nest_guard_rotated is False
    assert inspect.signature(tc._drop_nested).parameters["rotated"].default is False
    assert inspect.signature(tc.detect_text_clusters).parameters["nest_guard_rotated"].default is False
    from digitizer_core import pipeline
    src = inspect.getsource(pipeline)
    assert '**({"nest_guard_rotated": True} if cfg.text_cluster_nest_guard_rotated else {})' in src


def test_the_rescued_door_and_the_house_group_keep_todays_drop():
    assert "_drop_nested(raw)\n" in inspect.getsource(tc._candidates)
    assert "_drop_nested(raw)" in inspect.getsource(tc._lettering_groups)
    assert "rotated" not in inspect.getsource(tc._lettering_groups)


GOLDEN_MD5 = FLAT_GOLDEN_MD5


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(GOLDEN_MD5))
@pytest.mark.parametrize("on", [False, True])
def test_goldens_are_byte_identical_off_and_on(fixture, on):
    """OFF is the engine as it was. ON too: the three flat goldens carry no turned
    badge or baseline. The golden rides the live defaults (`test_pins_are_frozen`'s
    rule 1 exception), so this does too."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False,
                                            text_cluster_nest_guard_rotated=on))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == GOLDEN_MD5[fixture]
