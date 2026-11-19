"""3D puff (docs/superpowers/specs/2026-11-19-3d-puff-design.md): config switch,
constants, the per-shape eligibility test, and one shape's construction
(end-capped puff satin, ties, tack-down)."""
from __future__ import annotations

import math
import statistics
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.stage6_puff import puff_eligible, wants_puff


def _region(w_mm: float, h_mm: float = 30.0, **meta):
    return SimpleNamespace(polygon=box(0, 0, h_mm, w_mm), meta=dict(meta))


def test_puff_off_by_default():
    cfg = PipelineConfig()
    assert cfg.puff is False
    assert cfg.puff_mode == "all"


def test_wants_puff_modes():
    off = PipelineConfig(puff=False)
    assert wants_puff(_region(4, puff=True), off) is False
    assert wants_puff(_region(4), off) is False

    allm = PipelineConfig(puff=True, puff_mode="all")
    assert wants_puff(_region(4), allm) is True
    assert wants_puff(_region(4, puff=False), allm) is False
    assert wants_puff(_region(4, puff=True), allm) is True

    sel = PipelineConfig(puff=True, puff_mode="select")
    assert wants_puff(_region(4), sel) is False
    assert wants_puff(_region(4, puff=False), sel) is False
    assert wants_puff(_region(4, puff=True), sel) is True


def test_puff_eligible_width():
    cfg = PipelineConfig(puff=True)
    assert puff_eligible(_region(4), cfg) == (True, "")
    # Thin uses the skeleton mean (reads 1.8 as 1.9); wide uses the widest
    # inscribed circle, which is exact on a bar (the mean read 14 as 9.8).
    assert puff_eligible(_region(1.8), cfg) == (False, "too thin for foam (1.9 mm)")
    assert puff_eligible(_region(14), cfg) == (False, "too wide to puff (14.0 mm)")


def test_puff_eligible_ignores_flat_satin_ceiling():
    # 8 mm is past the flat satin ceiling (5.0) but inside the puff band.
    assert puff_eligible(_region(8), PipelineConfig(puff=True)) == (True, "")


def test_puff_eligible_ring_uses_ring_width_not_hole_blind_circle():
    from shapely.geometry import Point
    ring = Point(0, 0).buffer(10, 64).difference(Point(0, 0).buffer(6, 64))
    reg = SimpleNamespace(polygon=ring, meta={})
    assert puff_eligible(reg, PipelineConfig(puff=True)) == (True, "")


def test_puff_eligible_multipolygon_does_not_raise():
    from shapely.geometry import MultiPolygon
    mp = MultiPolygon([box(0, 0, 30, 4), box(0, 20, 30, 24)])
    reg = SimpleNamespace(polygon=mp, meta={})
    assert puff_eligible(reg, PipelineConfig(puff=True)) == (True, "")


# --- Task 3: construction for one shape ------------------------------------

BAR = box(0, 0, 30, 4)  # 4 x 30 mm bar, short ends at x=0 and x=30
RING = Point(0, 0).buffer(10, 64).difference(Point(0, 0).buffer(6, 64))
TEE = unary_union([box(0, 0, 30, 4), box(13, 4, 17, 24)])


def _puff(poly):
    from digitizer_core.stage6_puff import puff_shape
    return puff_shape(poly, "p", PipelineConfig(puff=True))


def _all_points(runs):
    return [p for r in runs for p in r.points]


def _covered(segment: LineString, pts, reach=0.3, step=0.05) -> float:
    """Fraction of `segment` within `reach` of some needle point."""
    n = max(1, int(segment.length / step))
    hit = 0
    for k in range(n + 1):
        q = segment.interpolate(k / n, normalized=True)
        if any(math.hypot(q.x - x, q.y - y) <= reach for x, y in pts):
            hit += 1
    return hit / (n + 1)


def test_puff_no_underlay():
    runs = _puff(BAR)
    assert runs
    assert all(r.kind != stitches.UNDERLAY for r in runs)


def test_puff_density():
    runs = [max(_puff(BAR), key=lambda r: len(r.points))]  # the top satin
    gaps = []
    for r in runs:
        pts = r.points[r.tie_in_pts:]
        mids = [((pts[i][0] + pts[i + 1][0]) / 2) for i in range(0, len(pts) - 1, 2)]
        gaps += [abs(b - a) for a, b in zip(mids, mids[1:])]
    assert abs(statistics.median(gaps) - machine.PUFF_SATIN_SPACING_MM) <= 0.02


@pytest.mark.parametrize("x", [0.0, 30.0])
def test_puff_ends_closed(x):
    pts = _all_points(_puff(BAR))
    assert _covered(LineString([(x, 0), (x, 4)]), pts) >= 0.8


def test_puff_end_caps_sew_before_top_satin():
    runs = _puff(BAR)
    top = max(range(len(runs)), key=lambda i: len(runs[i].points))
    reach = machine.PUFF_CAP_DEPTH_MM + 0.01
    caps = [i for i, r in enumerate(runs)
            if r.kind != stitches.TRAVEL and all(min(x, 30 - x) <= reach for x, _ in r.points[r.tie_in_pts:])]
    assert len(caps) == 2  # one per short end
    assert all(i < top for i in caps)


def test_puff_counter_closed():
    from digitizer_core.stage6_puff import puff_tackdown
    pts = _all_points(_puff(RING))
    inner = LineString(RING.interiors[0].coords)
    assert _covered(inner, pts) >= 0.8

    tack = puff_tackdown([RING], ["p"], PipelineConfig(puff=True))
    for ring in (RING.exterior, RING.interiors[0]):
        line = LineString(ring.coords)
        assert any(
            len(r.points) > 3
            and max(line.distance(Point(p)) for p in r.points) <= 0.3
            for r in tack
        ), "no tack-down run round this ring"


def test_puff_tackdown_is_inset():
    from digitizer_core.stage6_puff import puff_tackdown
    tack = puff_tackdown([BAR], ["p"], PipelineConfig(puff=True))
    assert len(tack) == 1
    inset = BAR.buffer(-machine.PUFF_INSET_MM, join_style=2)
    for p in tack[0].points:
        assert abs(inset.exterior.distance(Point(p))) < 1e-6
    assert tack[0].points[0] == tack[0].points[-1]  # the ring closes


def _bounce(seq) -> bool:
    return all(seq[i] == seq[i + 2] for i in range(len(seq) - 2)) and \
        all(0 < math.dist(a, b) <= machine.TIE_STITCH_MM + 1e-9
            for a, b in zip(seq, seq[1:]))


def test_puff_ties():
    n = machine.PUFF_TIE_STITCHES
    for poly in (BAR, RING):
        runs = _puff(poly)
        first, last = runs[0], runs[-1]
        assert first.tie_in_pts == n
        assert _bounce(first.points[:n + 1])
        assert _bounce(last.points[-(n + 1):])
    # tie_run's own default is untouched.
    assert len(stitches.tie_run((0, 0), (5, 0)).points) == machine.TIE_STITCHES + 2


def test_puff_junction_overlap():
    # The stem must run into the bar by at least the overlap, not butt it.
    runs = [r for r in _puff(TEE) if r.kind == stitches.SATIN]
    stem_low = min(
        min(p[1] for p in r.points)
        for r in runs if min(p[0] for p in r.points) > 10
    )
    assert stem_low <= 4.0 - machine.PUFF_JUNCTION_OVERLAP_MM


def test_puff_tee_caps_only_free_ends():
    pts = _all_points(_puff(TEE))
    # bar ends and the stem's top are free; all three close.
    assert _covered(LineString([(0, 0), (0, 4)]), pts) >= 0.8
    assert _covered(LineString([(30, 0), (30, 4)]), pts) >= 0.8
    assert _covered(LineString([(13, 24), (17, 24)]), pts) >= 0.8
