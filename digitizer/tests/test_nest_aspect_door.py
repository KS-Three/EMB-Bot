"""`cfg.extra["text_cluster_nest_door_aspect"]` (2026-11-07, built OFF): a letter turned
on a ring joins its line.

The letter door reads a glyph's aspect off its axis-aligned box, and a letter on the
side of a ring lies on its back: its height runs along x, its box reads wide, and the
door refuses it (`textcluster.ASPECT_RATIO_MAX` 1.4). Bridge's ring at 63.3 mm: nine
letters tag as one line and the two on its left side (axis aspect 1.61 / 1.57) do not.

The minimum-area rectangle alone has no "up" -- the two refused letters' rectangles
read long/short 1.76-1.79 and the line's own upright letters 1.55-1.72 -- so ON reads
the rectangle in the frame it shares with a line-mate: the side pointing nearer the
mate is the glyph's width (`_turned_candidate`). A region the door refused as too
wide that, so read, passes the door's own aspect, height and stroke bounds and links
to a member of a tagged line joins that line (`_adopt_turned`); it never makes or
bridges one. OFF: byte for byte.
"""
from __future__ import annotations

import hashlib
import inspect
import json
import math
import random

import cv2
import pytest
from shapely import affinity
from shapely.geometry import box

from digitizer_core import PipelineConfig, digitize
from digitizer_core import textcluster as tc
from digitizer_core.regions import Region

from .conftest import FLAT_GOLDEN_MD5, TESTDATA

FLAG = "text_cluster_nest_door_aspect"


def _region(sid: str, poly) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=float(poly.area))


def _bar(cx: float, cy: float, turn_deg: float, w: float = 1.2, h: float = 6.0):
    """A `w` x `h` stroke (an I) centred on (cx, cy), turned `turn_deg` about its centre."""
    return affinity.rotate(box(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2), turn_deg, origin=(cx, cy))


def _arc(r: float = 20.0, step: float = 12.0, last: float = 180.0) -> list[Region]:
    """Letters set on a ring of radius `r`, upright at the top (90 deg) and turned with
    the ring every `step` degrees counter-clockwise to `last`: at 180 deg the letter
    lies on its back."""
    out, n = [], 0
    pos = 90.0
    while pos <= last + 1e-9:
        th = math.radians(pos)
        out.append(_region(f"A{n:02d}", _bar(r * math.cos(th), r * math.sin(th), pos - 90.0)))
        n, pos = n + 1, pos + step
    return out


def _tagged(regions) -> dict[str, str | None]:
    return {r.shape_id: r.meta.get("text_cluster_id") for r in regions}


def _axis_aspect(r: Region) -> float:
    x0, y0, x1, y1 = r.polygon.bounds
    return (x1 - x0) / (y1 - y0)


# --- the scene is what it says -------------------------------------------------------

def test_the_ring_scene():
    regions = _arc()
    turns = [i * 12.0 for i in range(len(regions))]
    refused = [r.shape_id for r, t in zip(regions, turns) if _axis_aspect(r) > tc.ASPECT_RATIO_MAX]
    assert refused == ["A05", "A06", "A07"]                  # turned 60, 72 and 84 deg
    assert _axis_aspect(regions[-1]) > tc.ASPECT_RATIO_MAX   # 90 deg: on its back
    assert regions[-1].shape_id == "A07"
    # the rectangle alone: every letter reads 5.0 long/short, upright or on its back
    for r in regions:
        (_c, (w, h), _a) = cv2.minAreaRect(tc.get_coordinates(r.polygon.exterior).astype("float32"))
        assert abs(max(w, h) / min(w, h) - 5.0) < 1e-3


# --- the frame ------------------------------------------------------------------------

def _mate_at(x: float, y: float) -> tc._Candidate:
    poly = box(x - 0.6, y - 3.0, x + 0.6, y + 3.0)
    return tc._Candidate(region=_region("M", poly), height_mm=6.0, width_mm=1.2,
                         stroke_mean_mm=0.6, stroke_cv=0.1, cx=x, cy=y)


def _turned(poly):
    r = _region("T", poly)
    rect = cv2.minAreaRect(tc.get_coordinates(poly.exterior).astype("float32"))
    stats = tc._skeleton_stroke_stats(r)
    return r, rect, stats


@pytest.mark.parametrize("turn", [90.0, 75.0, -60.0, 120.0])
def test_the_side_toward_the_mate_is_the_width(turn):
    """A letter on its back with its line-mate along its baseline reads 1.2 wide and
    6 tall in that frame, whatever the rectangle's own angle convention."""
    r, rect, stats = _turned(_bar(0.0, 0.0, turn))
    th = math.radians(turn)                                  # the baseline turns with the letter
    c = tc._turned_candidate(r, rect, stats, _mate_at(5.0 * math.cos(th), 5.0 * math.sin(th)))
    assert c is not None
    assert abs(c.width_mm - 1.2) < 1e-3 and abs(c.height_mm - 6.0) < 1e-3


def test_a_mate_across_the_baseline_reads_it_wide_and_refuses_it():
    """The same bar with the mate off its END: the frame makes it 6 wide and 1.2 tall,
    aspect 5, and the letter door's own bound refuses that reading."""
    r, rect, stats = _turned(_bar(0.0, 0.0, 90.0))           # lies along x
    assert tc._turned_candidate(r, rect, stats, _mate_at(8.0, 0.0)) is None


def test_the_doors_height_bound_applies_to_the_turned_reading():
    r, rect, stats = _turned(_bar(0.0, 0.0, 90.0, w=0.3, h=1.2))   # 1.2 mm tall when read upright
    assert tc._turned_candidate(r, rect, stats, _mate_at(0.0, 3.0)) is None


# --- the tagger -----------------------------------------------------------------------

@pytest.mark.parametrize("kw", [{}, {"wide_letters": True, "part_touching": True},
                                {"part_touching": True}, {"nest_guard": True}])
def test_off_the_ring_side_is_refused_and_on_it_joins_the_line(kw):
    off, on = _arc(), _arc()
    tc.detect_text_clusters(off, None, **kw)
    tc.detect_text_clusters(on, None, nest_door_aspect=True, **kw)
    t_off, t_on = _tagged(off), _tagged(on)
    line = {"A00", "A01", "A02", "A03", "A04"}
    if kw.get("wide_letters"):
        line.add("A05")            # axis aspect 1.44: `_adopt_wide` (up to 1.8) already takes it
    assert {k for k, v in t_off.items() if v} == line
    assert len({t_off[k] for k in line}) == 1
    assert all(v is not None for v in t_on.values())
    assert len(set(t_on.values())) == 1                      # one line, the ring's
    assert t_on["A07"] != t_off["A00"]                       # its id names its new members


def test_off_is_the_tagger_as_it_was():
    """No kwarg and nest_door_aspect=False tag identically (the default path)."""
    a, b = _arc(), _arc()
    tc.detect_text_clusters(a, None, part_touching=True, wide_letters=True)
    tc.detect_text_clusters(b, None, part_touching=True, wide_letters=True, nest_door_aspect=False)
    assert _tagged(a) == _tagged(b)
    assert inspect.signature(tc.detect_text_clusters).parameters["nest_door_aspect"].default is False


def test_it_never_makes_a_line():
    """Only letters on their back, in a column: the door refuses every one, no line
    is tagged, and ON has nothing to join."""
    regions = [_region(f"S{i}", _bar(0.0, 3.0 * i, 90.0)) for i in range(5)]
    assert all(_axis_aspect(r) > tc.ASPECT_RATIO_MAX for r in regions)
    tc.detect_text_clusters(regions, None, nest_door_aspect=True, part_touching=True)
    assert all(v is None for v in _tagged(regions).values())


def test_a_wide_bar_beside_a_line_is_not_a_letter():
    """A 12 x 5 bar at the end of a line of 6 mm letters, and one above it: read along
    the line it is wide (aspect 2.4, refused); read across it is 12 mm tall against
    letters of 6 (no link). Neither joins."""
    letters = [_region(f"L{i}", _bar(3.0 * i, 0.0, 0.0)) for i in range(4)]
    beside = _region("Xb", box(12.0, -2.5, 24.0, 2.5).difference(box(13.0, -1.5, 23.0, 1.5)))
    above = _region("Xa", box(-1.0, 6.0, 11.0, 11.0).difference(box(0.0, 7.0, 10.0, 10.0)))
    regions = letters + [beside, above]
    tc.detect_text_clusters(regions, None, nest_door_aspect=True, part_touching=True)
    t = _tagged(regions)
    assert t["L0"] is not None and t["Xb"] is None and t["Xa"] is None


def test_a_bar_under_a_level_line_is_not_read_upright():
    """The first build's catch, MFab hat (104.9 mm): a 6.9 x 1.7 mm bar under the
    WELDING line, 13 mm from its nearest letter. The direction to that letter is
    nearly vertical, so it alone reads the bar as an upright 1.7 x 6.9 glyph; the
    line's own direction there is level, and the letter lies across it from the
    bar (63 deg), not along it: the bar is under the line, not beside it."""
    letters = [_region(f"L{i}", _bar(3.35 + 3.0 * i, 8.8, 0.0, w=1.7, h=6.8)) for i in range(6)]
    bar = _region("bar", box(-6.0, -3.7, 0.9, -2.0))
    regions = letters + [bar]
    tc.detect_text_clusters(regions, None, nest_door_aspect=True, part_touching=True)
    t = _tagged(regions)
    assert t["L0"] is not None and t["bar"] is None
    # the mate alone would have read it upright, and it would have linked
    r, rect, stats = _turned(bar.polygon)
    mate = tc._Candidate(region=letters[0], height_mm=6.8, width_mm=1.7, stroke_mean_mm=stats.mean_mm,
                         stroke_cv=0.1, cx=3.35, cy=8.8)
    c = tc._turned_candidate(r, rect, stats, mate)
    assert c is not None and abs(c.height_mm - 6.9) < 1e-3 and tc._linked(c, mate, tc.LETTER_HEIGHT_RATIO)
    assert tc._turned_candidate(r, rect, stats, mate, (1.0, 0.0)) is None


def test_the_ring_end_still_joins_with_its_bent_line():
    """Bridge's geometry, hat at 63.3 mm: the ring's local direction at its last
    tagged letter is 32 deg, the refused letter's rectangle (4.07 x 2.31, -9 deg)
    splits its sides 41 / 49 deg from that -- and the letter lies 22 deg off the
    line, along it. It reads 2.31 wide, 4.07 tall."""
    poly = affinity.rotate(box(-2.036, -1.155, 2.036, 1.155), -8.96, origin=(0, 0))
    poly = affinity.translate(poly, -13.85, 6.19)
    r, rect, stats = _turned(poly)
    mate = _mate_at(-12.1, 8.6)
    th = math.radians(32.0)
    c = tc._turned_candidate(r, rect, stats, mate, (math.cos(th), math.sin(th)))
    assert c is not None and abs(c.width_mm - 2.31) < 0.01 and abs(c.height_mm - 4.07) < 0.01


def test_another_ink_does_not_join():
    regions = _arc()
    for r in regions[5:]:
        r.thread_index = 1
    tc.detect_text_clusters(regions, None, chart=_TwoInks(), nest_door_aspect=True)
    t = _tagged(regions)
    assert all(t[r.shape_id] is None for r in regions[5:]) and t["A00"] is not None


class _TwoInks:
    """A chart whose two threads are far apart (`_same_ink` reads delta_e)."""
    def delta_e(self, a, b):
        return 0.0 if a == b else 80.0


def test_the_result_does_not_depend_on_input_order():
    base = _arc(step=10.0)
    want = None
    rng = random.Random(0)
    for _ in range(6):
        regions = _arc(step=10.0)
        rng.shuffle(regions)
        tc.detect_text_clusters(regions, None, nest_door_aspect=True, part_touching=True)
        got = _tagged(regions)
        want = want or got
        assert got == want
    assert len(base) == len(want) and all(v is not None for v in want.values())


# --- wiring and OFF ------------------------------------------------------------------

def test_the_flag_is_an_extra_and_is_off():
    assert FLAG not in PipelineConfig().extra
    from digitizer_core import pipeline
    src = inspect.getsource(pipeline)
    assert '**({"nest_door_aspect": True}\n' in src
    assert f'if (cfg.extra or {{}}).get("{FLAG}") else {{}}))' in src


def _md5(coords) -> str:
    return hashlib.md5(json.dumps(coords).encode()).hexdigest()


@pytest.mark.parametrize("fixture", sorted(FLAT_GOLDEN_MD5))
@pytest.mark.parametrize("on", [False, True])
def test_goldens_are_byte_identical_off_and_on(fixture, on):
    """OFF is the engine as it was. ON too: the three flat goldens set no letter on a
    ring. The golden rides the live defaults (`test_pins_are_frozen`'s rule 1
    exception), so this does too."""
    golden = json.loads((TESTDATA / "flat_lane_golden.json").read_text(encoding="utf-8"))[fixture]
    assert _md5(golden["stitch_coords"]) == FLAT_GOLDEN_MD5[fixture]
    _result, plan = digitize(TESTDATA / fixture,
                             PipelineConfig(target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False,
                                            extra={FLAG: True} if on else {}))
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim]
              for _, r in plan.iter_runs() for x, y in r.points]
    assert _md5(coords) == FLAT_GOLDEN_MD5[fixture]
