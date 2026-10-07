"""`cfg.satin_outer_rail_pitch`: the outer rail of a curved satin column holds
the design pitch.

Hotel Fremont, 2026-10-06 (`.claude/memory/lettering-thickness-fremont-2026-10-06.md`):
the pro's DST sews the O's outer rail at 0.33 mm between penetrations and
short-stitches the inner; ours read 0.53. Stations were spaced evenly along
the SPINE, so on a bend the outer rail opened to 1.3x the pitch before the
refinement fired, and the inner-rail crowding clamp then refused the
insertion. ON, the body of a column is re-stationed evenly along its OUTER
rail; the short-stitch guard retracts alternate inner penetrations where the
inner rail crowds, which is the professional construction. OFF is byte for
byte what shipped.

The ring below is the Fremont O at 80 mm: 1.2 mm wide on a 2.95 mm outer
radius. Rails are read by parity (A, B, A, B ... -- `test_satin.py` says why
that is safe) and sorted into outer/inner by radius.
"""
from __future__ import annotations

import math

import numpy as np
from shapely.geometry import Point, Polygon

from digitizer_core import machine
from digitizer_core.stage6_satin import satin_shape
from tests.test_satin import O_RING, _cross_rotations, _satin_runs

R_OUT, R_IN = 2.95, 1.75
FREMONT_O = Polygon(
    [(math.cos(t) * R_OUT, math.sin(t) * R_OUT) for t in np.linspace(0, 2 * math.pi, 120, endpoint=False)],
    [[(math.cos(t) * R_IN, math.sin(t) * R_IN) for t in np.linspace(2 * math.pi, 0, 80, endpoint=False)]],
)
BAR = Polygon([(0, 0), (24, 0), (24, 2), (0, 2)])


def _rail_pitches(poly, **kw):
    runs, _ = satin_shape(poly, "S1", underlay_style="none", trim_at_mm=3.0, outer_rail_pitch=True, **kw)
    outer: list[float] = []
    inner: list[float] = []
    short = 0
    total = 0
    mid = (R_OUT + R_IN) / 2
    for r in runs:
        if r.kind != "satin":
            continue
        pts = r.points
        for rail in (pts[0::2], pts[1::2]):
            for a, b in zip(rail, rail[1:]):
                d = math.dist(a, b)
                if d < 0.03:
                    continue
                ra = math.hypot(*a)
                (outer if ra > mid else inner).append(d)
        for a, b in zip(pts, pts[1:]):
            w = math.dist(a, b)
            if w < 0.5:
                continue
            total += 1
            if w < 0.8 * (R_OUT - R_IN):
                short += 1
    return np.asarray(outer), np.asarray(inner), short, total


def test_ring_outer_rail_sits_on_the_pitch():
    outer, inner, short, total = _rail_pitches(FREMONT_O)
    assert len(outer) > 20 and len(inner) > 20
    p50, p90 = np.percentile(outer, 50), np.percentile(outer, 90)
    assert p50 <= machine.SATIN_SPACING_MM * 1.05, f"outer rail median {p50:.3f} mm"
    assert p90 <= machine.SATIN_SPACING_MM * 1.15, f"outer rail p90 {p90:.3f} mm"


def test_ring_inner_rail_is_short_stitched_not_crowded():
    """Holding the outer rail at 0.4 on this ring puts full crosses 0.24 mm
    apart on the inner rail; the guard retracts every other one, so what
    lands ON the inner rail stays at or above the same-hole threshold and
    the retracted ends read as short crosses -- the pro's 22%."""
    outer, inner, short, total = _rail_pitches(FREMONT_O)
    on_rail = inner[inner >= machine.SATIN_SHORT_STITCH_AT_MM * 0.9]
    assert len(on_rail) / len(inner) >= 0.5, "inner rail crowded under the guard threshold"
    assert short / total >= 0.15, f"only {short}/{total} short crosses; the inner rail is not short-stitched"


def test_ring_under_rail_comp_keeps_the_outer_pitch():
    """`cfg.satin_rail_comp` pushes both rails out by the pull AFTER the
    stations are set; the outer rail's pitch grows by (r + pull) / r, which
    on this ring is 10%. That is geometry, pinned here so it cannot drift."""
    outer, _, _, _ = _rail_pitches(FREMONT_O, rail_comp_mm=0.3)
    p50 = np.percentile(outer, 50)
    assert p50 <= machine.SATIN_SPACING_MM * 1.05 * (R_OUT + 0.3) / R_OUT, f"outer rail median {p50:.3f} mm under rail comp"


def test_off_is_byte_identical_and_a_straight_bar_is_unchanged_on():
    """OFF is the pre-flip emitter: `outer_rail_pitch=False` is the verbatim
    per-interval rule (the default is ON since 2026-10-06, Kent's call). And
    ON, a straight bar is the floor case: its outer rail IS its spine and
    its stations already sit at the pitch, so re-stationing along the rail
    lands exactly where they were -- OFF and ON agree on it to the byte."""
    off, _ = satin_shape(BAR, "S1", underlay_style="none", trim_at_mm=3.0, outer_rail_pitch=False)
    dflt, _ = satin_shape(BAR, "S1", underlay_style="none", trim_at_mm=3.0)
    on, _ = satin_shape(BAR, "S1", underlay_style="none", trim_at_mm=3.0, outer_rail_pitch=True)
    assert [r.points for r in dflt] == [r.points for r in on]
    assert [r.points for r in off] == [r.points for r in on]
    satin = [r for r in on if r.kind == "satin"]
    assert len(satin) == 1
    pts = satin[0].points
    adv = [math.dist(a, b) for rail in (pts[0::2], pts[1::2]) for a, b in zip(rail, rail[1:])]
    adv = [d for d in adv if d > 0.03]
    body = sorted(adv)[len(adv) // 10: -len(adv) // 10]
    assert max(body) - min(body) < 0.02, "a straight bar's stations are no longer even"
    assert abs(np.median(body) - machine.SATIN_SPACING_MM) < 0.03
    # and the pre-flip ring is what it was: 0.46 on the outer rail, no short stitches
    outer_off = []
    for r in [r for r in satin_shape(O_RING, "S1", underlay_style="none", trim_at_mm=3.0, outer_rail_pitch=False)[0] if r.kind == "satin"]:
        p = r.points
        for rail in (p[0::2], p[1::2]):
            outer_off += [math.dist(a, b) for a, b in zip(rail, rail[1:]) if math.hypot(*a) > 8.75 and math.dist(a, b) > 0.03]
    assert 0.44 <= float(np.median(outer_off)) <= 0.47, float(np.median(outer_off))


def test_on_the_test_ring_crosses_turn_evenly_and_only_the_lean_legs_alternate():
    """`test_satin.py`'s archetype pin reads the O ring at 3.1 deg OFF with
    a 5.0 bar. ON it reads 5.5, and that is not spray: the ring's body goes
    from 138 to 168 stations (0.46 -> 0.40 on the outer rail), the inner rail
    crowds under the short-stitch threshold, and every OTHER inner
    penetration is retracted 0.6 mm. The CROSSES still turn evenly (2.3 to
    2.5 deg each); what the pin also compares is each LEAN leg with the
    next, and a lean leg to a retracted penetration sits ~2.9 deg off one to
    a full penetration. Pinned at the mechanism: crosses even, leans
    alternating by a bounded amount, retraction regular (every other, not
    wherever float noise puts an interval a hair under the threshold)."""
    runs, _ = satin_shape(O_RING, "S1", underlay_style="none", trim_at_mm=3.0, outer_rail_pitch=True)
    satin = [r for r in runs if r.kind == "satin"]
    assert len(satin) == 1
    rot = _cross_rotations(satin)
    assert max(rot) <= 6.0, f"ON the ring sprays: worst {max(rot):.1f} deg"
    pts = np.asarray(satin[0].points)
    a, b = pts[0::2], pts[1::2]
    ra, rb = np.hypot(*a.T), np.hypot(*b.T)
    inner = a if np.median(ra) < np.median(rb) else b
    retracted = np.hypot(*inner.T) > 7.6
    idx = np.where(retracted)[0]
    assert retracted.sum() >= 0.4 * len(inner), "the inner rail is not short-stitched"
    odd = int((idx % 2 == 1).sum())
    assert odd >= 0.9 * len(idx), f"retraction is irregular: {odd} odd of {len(idx)}"


def test_on_the_hole_side_rail_still_reaches_the_counter_edge():
    """`test_satin.py::test_the_hole_side_rail_reaches_the_counter_edge`
    pins the median inner penetration on the hole's edge. ON, every other
    inner penetration is a deliberate short stitch, so the ON pin reads the
    on-rail quartile instead. No bound is put on how far IN the retracted
    half sits: it is the guard's 0.6 mm cap on top of wherever the ladder
    put the on-rail point (up to 0.13 mm inside the edge on this ring --
    measured 2026-10-06, retracted median 8.16, max 8.23), and the guard's
    own tests pin the cap."""
    outer = Point(0.0, 0.0).buffer(10.0, quad_segs=64)
    ring = outer.difference(Point(0.0, 0.0).buffer(7.5, quad_segs=64))
    runs, report = satin_shape(ring, "S1", underlay_style="none", trim_at_mm=3.0, outer_rail_pitch=True)
    assert not report["empty"]
    r = np.array([math.hypot(x, y) for run in runs if run.kind == "satin" for x, y in run.points])
    inner, outer_pts = r[r < 8.75], r[r > 8.75]
    assert inner.size > 100 and outer_pts.size > 100
    assert float(np.percentile(inner, 25)) <= 7.5 + 0.06, float(np.percentile(inner, 25))
    assert float(inner.min()) >= 7.5 - 0.03, float(inner.min())
    assert float(np.median(outer_pts)) >= 10.0 - 0.06, float(np.median(outer_pts))
