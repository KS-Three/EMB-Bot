"""`cfg.satin_cap_recentre` — a free end's spine must not ride a cap fork into one corner.

The defect (2026-09-19, found from the outline side by `tools/edge_wobble.py`'s
`unsewn`): a stem whose one edge leans THREE DEGREES sews its cap into one
corner and abandons the other. The medial axis of a flat cap forks toward both
corners; on a plain bar the forks are twins and the pruner drops both, on a
leaning stem one is a hair longer, survives as the spine's tail, and
`_retract_cap_corner` stops walking it back at 0.8 of the half-width — which a
fork's first millimetre still reads. `_extend_to_cap` then extends along the
diagonal and lands ON the corner.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import MultiLineString, Point, Polygon

from digitizer_core import PipelineConfig, stage6_satin as S, stitches

BAR = Polygon([(0, 0), (4.6, 0), (4.6, 14), (0, 14)])
# MARINE's "I", reduced: the left edge leans 0.8 mm over 14 — 3.3 degrees.
LEANING_STEM = Polygon([(0.8, 0), (4.6, 0), (4.6, 14), (0, 14)])
SLANT_CAP = Polygon([(0, 1.5), (4.6, 0), (4.6, 14), (0, 14)])
# A wedge: the corridor pinches to nothing with NO kink. A taper, not a fork.
TAPER = Polygon([(0, 0), (3.0, 0), (1.7, 16), (1.3, 16)])


def sew(poly: Polygon, **kw):
    runs, _report = S.satin_shape(poly, "t", underlay_style="auto", trim_at_mm=3.0, **kw)
    return runs


def flat(runs) -> list:
    return [(r.kind, [(round(x, 6), round(y, 6)) for x, y in r.points]) for r in runs]


def corner_gaps(poly: Polygon, runs) -> dict[tuple[float, float], float]:
    segs = [(r.points[i], r.points[i + 1]) for r in runs if r.kind == stitches.SATIN
            for i in range(len(r.points) - 1)]
    thread = MultiLineString(segs)
    return {(x, y): thread.distance(Point(x, y)) for x, y in list(poly.exterior.coords)[:-1]}


def test_the_defect_is_real_with_the_flag_off():
    gaps = corner_gaps(LEANING_STEM, sew(LEANING_STEM))
    assert gaps[(0.8, 0.0)] > 0.9          # 1.11 measured: the abandoned corner
    assert gaps[(4.6, 0.0)] < 0.6          # ...while its twin is sewn right into
    assert max(corner_gaps(BAR, sew(BAR)).values()) < 0.5      # a plain bar never had it


def test_on_both_cap_corners_are_reached():
    gaps = corner_gaps(LEANING_STEM, sew(LEANING_STEM, cap_recentre=True))
    assert max(gaps.values()) < 0.55, gaps


def test_on_the_cap_ends_square_not_in_a_point():
    # The old tail tapered the column to zero width at the corner. The last
    # real cross of a square end spans most of the cap.
    runs = sew(LEANING_STEM, cap_recentre=True)
    pts = [p for r in runs if r.kind == stitches.SATIN for p in r.points]
    top = sorted(pts, key=lambda p: p[1])[:4]
    assert max(p[0] for p in top) - min(p[0] for p in top) > 3.0


def test_a_slanted_cap_is_left_alone_because_cutting_it_is_harm():
    """On a cap that is not square to the stem the fork is what REACHES the
    acute corner, and a square rebuilt end cannot cover both: the first cut of
    this flag took that corner 0.48 -> 1.23 mm bare. A slanted cap wants its
    last crosses leaned to the cap face, which is a different repair (the
    "leaning crosses at a square cap" mechanism, DOCTRINE 2026-09-19). Until
    that exists the end sews exactly as it did."""
    assert flat(sew(SLANT_CAP, cap_recentre=True)) == flat(sew(SLANT_CAP))


@pytest.mark.parametrize("poly", [BAR, TAPER], ids=["bar", "taper"])
def test_no_fork_no_change(poly):
    """A bar's forks are pruned before this ever looks, and a taper pinches
    with no kink. Neither is a fork, so ON is byte-identical to OFF."""
    assert flat(sew(poly, cap_recentre=True)) == flat(sew(poly))


def test_a_curved_columns_flat_end_is_no_worse():
    """A flat-ended "C". Its ends DO fork and ARE cut, and it is a wash: the
    rebuild is a straight extension on a curving axis, so the inner corner
    gives 0.08 mm (0.77 -> 0.85) and the outer takes 0.07 (0.41 -> 0.34).
    The contract is "no worse", not "untouched" — tuning the guards until a
    wash read byte-identical would be fitting them to this one polygon. The
    inner corner of a curved column is bare either way, for a reason this
    flag does not address (the extension is straight)."""
    c = Point(0, 0).buffer(8.0, 128).difference(Point(0, 0).buffer(5.0, 128)).difference(
        Polygon([(0, 0), (12, -5), (12, 5)]))
    a = math.atan2(5, 12)
    caps = [(r * math.cos(a), s * r * math.sin(a)) for r in (5.0, 8.0) for s in (1, -1)]

    def gaps(runs):
        segs = [(r.points[i], r.points[i + 1]) for r in runs if r.kind == stitches.SATIN
                for i in range(len(r.points) - 1)]
        thread = MultiLineString(segs)
        return [thread.distance(Point(p)) for p in caps]

    off, on = gaps(sew(c)), gaps(sew(c, cap_recentre=True))
    assert max(on) <= max(off) + 0.1
    assert sum(on) <= sum(off) + 0.05


def test_curvature_alone_is_never_a_kink():
    # Round-ended C: the spine turns all the way to its tips, which are not pinched.
    arc = [(6.5 * math.cos(a), 6.5 * math.sin(a))
           for a in (0.5 + i * (2 * math.pi - 1.0) / 80 for i in range(81))]
    from shapely.geometry import LineString
    c = LineString(arc).buffer(1.5, 32)
    assert flat(sew(c, cap_recentre=True)) == flat(sew(c))


def test_the_flag_ships_off():
    assert PipelineConfig().satin_cap_recentre is False
