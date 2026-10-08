"""`cfg.satin_join_square` at a plain stroke's FREE END: a square cap sews
square to its face, and a slab hanging off it -- a T-junction slab, a foot
serif -- is sewn as its own column square to itself (2026-10-08).

The corner join (`tests/test_join_corner_straight.py`) left these as fans:
`_prune_spurs` reads a slab's two short skeleton arms as a cap's I-beam and
takes both, so the stem is a plain stroke with a free end whose spine hooks
into one of the slab's corners, and nothing owns the slab's wings -- the fan
into them was their only thread. Straightening the stem alone traded the fan
for bare wings (rendered on this H before the slab column was built).

The fixture is Hotel Fremont's H at 92.5 mm / patch, the corpus setting,
exactly as stage 7 handed it to `satin_shape` (`testdata/
fremont_H_slab_feet.json`, coordinate arrays at full precision). Its left
foot's wings belong to no stroke; its right foot keeps one wing as a stroke
of its own, which the slab column must not sew a second time.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

from digitizer_core import machine, stage6_satin
from digitizer_core.stage6_satin import satin_shape

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "testdata" / "fremont_H_slab_feet.json"


def _fixture():
    f = json.loads(FIXTURE.read_text(encoding="utf-8"))
    kw = dict(f["kwargs"])
    kw["max_width_mm"] = math.inf if kw["max_width_mm"] == "inf" else kw["max_width_mm"]
    kw["start_near"] = tuple(kw["start_near"])
    kw["end_near"] = tuple(kw["end_near"])

    def poly(rings):
        return Polygon(rings[0], rings[1:])
    return poly(f["poly_rings"]), poly(f["art_poly_rings"]), kw


def _runs(join_square):
    poly, art, kw = _fixture()
    runs, report = satin_shape(poly, "S1", art_poly=art, join_square=join_square, **kw)
    assert not report["empty"]
    return runs


def _bare(runs, region):
    thread = unary_union([LineString(r.points).buffer(machine.COVERAGE_THREAD_W_MM / 2)
                          for r in runs if r.kind in ("satin", "underlay", "run") and len(r.points) > 1])
    return region.difference(thread).area


def _feet():
    _poly, art, _kw = _fixture()
    x0, _y0, x1, y1 = art.bounds
    mid = 0.5 * (x0 + x1)
    # the bottom 0.95 mm of the letter is its feet (the slab is ~0.8 deep)
    return (box(x0, y1 - 0.95, mid, y1).intersection(art),
            box(mid, y1 - 0.95, x1, y1).intersection(art),
            box(x0 - 0.3, y1 - 0.95, mid, y1 + 0.3))


def _foot_cross_angles(runs, zone):
    """Directions (deg mod 180) of the satin crosses lying wholly in `zone`."""
    out = []
    for r in runs:
        if r.kind != "satin":
            continue
        for a, b in zip(r.points, r.points[1:]):
            if math.dist(a, b) >= 0.5 and zone.contains(LineString([a, b])):
                out.append(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180.0)
    return out


def _near(angles, target, tol=5.0):
    return sum(1 for a in angles if min(abs(a - target), 180.0 - abs(a - target)) <= tol)


def test_off_is_the_default_and_the_left_foot_is_bare_and_fanned():
    """OFF is the default (the byte-for-byte pin against the shipped joiner
    is the goldens in the full suite), and on it the H's left foot
    is the defect: half a square millimetre of its slab bare, and no cross
    in it square to the stem or to the slab -- the stem's end fans in."""
    poly, art, kw = _fixture()
    dflt, _ = satin_shape(poly, "S1", art_poly=art, **kw)
    off = _runs(False)
    assert [r.points for r in dflt] == [r.points for r in off]
    left, _right, zone = _feet()
    assert _bare(off, left) >= 0.4, f"the fixture's left foot is no longer bare OFF ({_bare(off, left):.3f} mm2)"
    angles = _foot_cross_angles(off, zone)
    assert _near(angles, 0.0) == 0, angles


def test_on_the_stem_lands_square_and_the_slab_is_sewn_square_to_itself():
    on = _runs(True)
    left, _right, zone = _feet()
    angles = _foot_cross_angles(on, zone)
    # the stem (vertical) crosses square to it, run down to the cap face ...
    assert _near(angles, 0.0) >= 2, angles
    # ... and the slab (horizontal) sewn as its own column, crosses square to IT
    assert _near(angles, 90.0) >= 2, angles
    assert _bare(on, left) <= 0.05, f"{_bare(on, left):.3f} mm2 of the left foot bare ON"


def test_on_covers_the_letter_and_does_not_resew_an_owned_wing():
    """The whole H is barer OFF than ON by more than half, and the right
    foot -- one wing already its own stroke -- is no barer ON (the slab
    column is cut against the strokes that already sew it, `_attach_slabs`)
    and gains no more than one short column's worth of penetrations."""
    _poly, art, _kw = _fixture()
    off, on = _runs(False), _runs(True)
    assert _bare(on, art) <= 0.5 * _bare(off, art), (_bare(off, art), _bare(on, art))
    _left, right, _zone = _feet()
    assert _bare(on, right) <= _bare(off, right) + 0.02
    n_off = sum(len(r.points) for r in off if r.kind == "satin")
    n_on = sum(len(r.points) for r in on if r.kind == "satin")
    assert n_off <= n_on <= n_off + 16, (n_off, n_on)


def test_a_slanted_terminal_is_left_alone():
    """A free end whose cap face is cut on a slant keeps its fan -- there the
    turning crosses ARE the construction (Enthusiast's S). A lens pointed at
    both ends: every free end the reading sees fails the face-slant gate
    (`_FACE_SLANT_MAX_DEG`), and nothing changes."""
    wedge = Polygon([(0.0, 0.0), (4.0, -0.5), (8.0, 0.0), (4.0, 0.5)])
    _poly, _art, kw = _fixture()
    kw = {k: v for k, v in kw.items() if k not in ("start_near", "end_near")}
    off, _ = satin_shape(wedge, "S1", art_poly=wedge, join_square=False, **kw)
    on, _ = satin_shape(wedge, "S1", art_poly=wedge, join_square=True, **kw)
    assert [r.points for r in on] == [r.points for r in off]


def test_a_narrowing_end_is_read_as_a_tip_and_left_alone():
    """The RATIO gate on its own: a 1 mm stem ending in a 0.3 mm nib with a
    square face passes the arm, line and slant gates, reads under
    `_SQUARE_END_RATIO` arm widths at its face, and so a spine hooked at
    that end is sewn exactly as it is with the flag off."""
    shape = Polygon([(0.0, -0.5), (7.5, -0.5), (7.5, -0.15), (9.5, -0.15),
                     (9.5, 0.15), (7.5, 0.15), (7.5, 0.5), (0.0, 0.5)])
    spine = [(0.1 * i, 0.0) for i in range(89)] + [(8.9, -0.04), (9.0, -0.08), (9.1, -0.12)]
    half = 0.5
    reading = stage6_satin._free_end_reading(spine, True, half, shape, None)
    assert reading is not None, "the end should pass the arm, line and slant gates"
    assert reading[0] < stage6_satin._SQUARE_END_RATIO and reading[1] is None, reading
    assert reading[2], "the fixture's end should read as hooked"
    st = stage6_satin.Stroke(spine=spine, free_start=False, free_end=True, closed=False)
    off = stage6_satin.satin_stroke(shape, st, half, join_square=False)
    on = stage6_satin.satin_stroke(shape, st, half, join_square=True)
    assert on == off
