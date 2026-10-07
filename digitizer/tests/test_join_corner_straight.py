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


def test_the_fixture_fans_off_and_the_default_is_on():
    """`join_square=False` is the pre-flip joiner, and on it the E's arms DO
    fan -- the reading the flag exists to move. Pinned so the fixture cannot
    quietly stop reproducing the defect (a rounded copy of this polygon
    already does not). The default is ON since 2026-10-06, Kent's call."""
    from digitizer_core import PipelineConfig
    poly, art, kw = _fixture()
    off, _ = satin_shape(poly, "S1", art_poly=art, join_square=False, **kw)
    dflt, _ = satin_shape(poly, "S1", art_poly=art, **kw)
    # the FUNCTION default stays False (every direct caller keeps the
    # pre-flip joiner); the CONFIG default is what stage 7 passes, and it is
    # True since the flip
    assert [r.points for r in dflt] == [r.points for r in off]
    assert PipelineConfig().satin_join_square is True
    events, columns = fan_ends([r.points for r in off if r.kind == "satin"])
    assert columns >= 4
    assert events >= 2, f"the E no longer fans OFF ({events} fan ends over {columns} columns)"


def test_on_the_arms_sew_square_to_their_slabs():
    runs = _runs(True)
    events, columns = fan_ends([r.points for r in runs if r.kind == "satin"])
    assert columns >= 4
    assert events == 0, f"{events} fan ends over {columns} columns with join_square on"
    # and it is a change of WHERE the crosses point, not of how many: the
    # same 116 satin penetrations either way (measured 2026-10-06)
    off = _runs(False)
    assert sum(len(r.points) for r in runs if r.kind == "satin") == \
        sum(len(r.points) for r in off if r.kind == "satin")


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
