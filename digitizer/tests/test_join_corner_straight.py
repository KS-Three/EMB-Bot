"""`cfg.satin_join_square`: a member that owns a join corner sews square up
to it, and the member that butts in starts square. The serif and junction
fans (Kent, 2026-10-06).

Hotel Fremont's E: `_split_sharp_corners` already cuts each arm from its
hanging slab serif (turn 59 deg at the artwork corner) and the arm owns the
corner. The fan came AFTER the cut: the medial axis of an L bends over about
one half-width on each side of the apex, the owner member's spine kept
those bent samples, and under the wordmark's house angle the last four or
five crosses leaned into the slab. The pro's arm runs square to the slab's
far edge and the slab is its own short column with crosses square to IT.

The fixture is that E, byte for byte as stage 7 handed it to `satin_shape`
(`testdata/fremont_E_join_corner.json`: planned polygon, artwork polygon,
walk anchors, every keyword) -- a clean synthetic L does not fan, because
the fan needs the house angle and the raster skeleton of a real letter. The
instrument is `tools/letter_band.fan_ends`, the one the Fremont measurement
used: a column whose crosses in its last 1.5 mm of rail lean more than
20 deg over its middle ones.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

from shapely import wkt
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import machine
from digitizer_core.stage6_satin import satin_shape

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from letter_band import fan_ends  # noqa: E402

FIXTURE = ROOT / "testdata" / "fremont_E_join_corner.json"


def _fixture():
    f = json.loads(FIXTURE.read_text(encoding="utf-8"))
    kw = dict(f["kwargs"])
    kw["max_width_mm"] = math.inf if kw["max_width_mm"] == "inf" else kw["max_width_mm"]
    kw["start_near"] = tuple(kw["start_near"])
    kw["end_near"] = tuple(kw["end_near"])
    return wkt.loads(f["poly_wkt"]), wkt.loads(f["art_poly_wkt"]), kw


def _runs(join_square):
    poly, art, kw = _fixture()
    runs, report = satin_shape(poly, "S1", art_poly=art, join_square=join_square, **kw)
    assert not report["empty"]
    return runs


def test_the_fixture_fans_off_and_the_flag_is_off_by_default():
    """OFF is the shipped joiner, and on it the E's arms DO fan -- the
    reading the flag exists to move. Pinned so the fixture cannot quietly
    stop reproducing the defect (a rounded copy of this polygon already
    does not)."""
    poly, art, kw = _fixture()
    off, _ = satin_shape(poly, "S1", art_poly=art, **kw)
    dflt, _ = satin_shape(poly, "S1", art_poly=art, join_square=False, **kw)
    assert [r.points for r in off] == [r.points for r in dflt]
    events, columns = fan_ends([r.points for r in off if r.kind == "satin"])
    assert columns >= 4
    assert events >= 2, f"the E no longer fans OFF ({events} fan ends over {columns} columns)"


def _middle_arm(runs):
    """The E's middle arm: the one satin run lying wholly in the letter's
    middle band (the arms and the stem all reach its top or bottom)."""
    mid = [r for r in runs if r.kind == "satin" and all(abs(y) < 1.2 for _x, y in r.points)]
    assert len(mid) == 1
    return mid[0].points


def _square_legs(points):
    """(x, deg mod 180) of every other cross of a run -- one leg kind of the
    zigzag, the one whose median runs nearest square (90 deg) across this
    horizontal arm; the other kind is the return leg, leaning forward."""
    legs = []
    for k in range(0, len(points) - 1):
        (ax, ay), (bx, by) = points[k], points[k + 1]
        legs.append((0.5 * (ax + bx), math.degrees(math.atan2(by - ay, bx - ax)) % 180.0))
    kinds = [legs[0::2], legs[1::2]]
    return min(kinds, key=lambda ks: abs(sorted(a for _x, a in ks)[len(ks) // 2] - 90.0))


def test_on_the_arms_sew_square_to_their_slabs():
    runs = _runs(True)
    events, columns = fan_ends([r.points for r in runs if r.kind == "satin"])
    # The three corner columns. The middle arm is a fourth column OFF, but
    # ON its body carries guard-pulled crosses (below) that break the strict
    # side-alternation `fan_ends`' column cutter needs, so it is read on its
    # own in the next test.
    assert columns >= 3
    assert events == 0, f"{events} fan ends over {columns} columns with join_square on"
    # and at the corners it is a change of WHERE the crosses point, not of
    # how many: each corner run keeps its penetration count (measured
    # 2026-10-06, re-read 2026-10-08)
    off = _runs(False)
    corner = lambda rs: sorted(len(r.points) for r in rs if r.kind == "satin" and r.points
                               is not None and not all(abs(y) < 1.2 for _x, y in r.points))
    assert corner(runs) == corner(off)


def test_on_the_middle_arm_ends_square_at_its_cap():
    """The middle arm is no corner: it ends in a chamfered square cap whose
    corner its skeleton hooks into, and OFF its square legs turn from 90 deg
    to 57 over the last half millimetre. ON (`_free_end_reading`: a square
    cap) its end is laid on the arm's line and every square leg holds within
    10 deg of the middle's. The price, pinned so it is seen: one more
    station (+2 penetrations), and three guard-pulled crosses mid-arm -- not
    this flag's mechanism but `satin_outer_rail_pitch` re-stationing a
    straight 3 mm body whose stations sit 3% over the pitch (PR body)."""
    x_end = max(x for x, _y in _middle_arm(_runs(False)))
    for flag, worst in ((False, 25.0), (True, 10.0)):
        legs = _square_legs(_middle_arm(_runs(flag)))
        body = sorted(a for x, a in legs if x < x_end - 1.0)
        ref = body[len(body) // 2]
        tip = [a for x, a in legs if x >= x_end - 0.5]
        turn = max(min(abs(a - ref), 180.0 - abs(a - ref)) for a in tip)
        if flag:
            assert turn <= worst, f"ON the middle arm's end still turns {turn:.1f} deg"
        else:
            assert turn >= worst, f"OFF the middle arm's end no longer fans ({turn:.1f} deg)"
    n = lambda rs: len(_middle_arm(rs))
    assert n(_runs(False)) <= n(_runs(True)) <= n(_runs(False)) + 2


def test_the_slab_corners_stay_covered():
    """Straightening the owner must not open the corner it owns: the
    artwork of the E's two hanging slabs stays under thread as well as it
    did OFF, to a tenth of a square millimetre."""
    poly, art, kw = _fixture()
    x1 = art.bounds[2]
    slabs = Polygon([(x1 - 1.0, art.bounds[1]), (x1, art.bounds[1]), (x1, art.bounds[3]), (x1 - 1.0, art.bounds[3])]).intersection(art)
    bare = {}
    for flag in (False, True):
        runs = _runs(flag)
        thread = unary_union([LineString(r.points).buffer(machine.COVERAGE_THREAD_W_MM / 2)
                              for r in runs if r.kind in ("satin", "underlay") and len(r.points) > 1])
        bare[flag] = slabs.difference(thread).area
    assert bare[True] <= bare[False] + 0.1, f"the slabs went barer: {bare[False]:.3f} -> {bare[True]:.3f} mm2"
    assert bare[True] <= 0.6, f"{bare[True]:.3f} mm2 bare in the slab column"
