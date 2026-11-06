"""`tools/polygon_profile.py` -- the polygon-native width profile measured as
defect 26's negative #9 (2026-11-06,
`docs/classifier-polygon-profile-2026-11-06.md`). Pins what the record says
the construction does, so a re-measure starts from the same instrument.

Cheap: hand-built polygons, no pipeline run.
"""
import math

import numpy as np
import pytest
from shapely.geometry import Point, Polygon, box

from digitizer_core import stage6_satin as s6
from tests.test_satin import BAR, C_STROKE, O_RING, T_SHAPE, _serrated_disc
from tools import polygon_profile as pp
from tools import ribbon_stability as rs


def _arc(n: int) -> Polygon:
    """A 2.5 mm curved ribbon whose walls are drawn with `n` vertices."""
    t = np.linspace(0.3, 4.0, n)
    return Polygon([(math.cos(x) * 14.5, math.sin(x) * 14.5) for x in t]
                   + [(math.cos(x) * 12.0, math.sin(x) * 12.0) for x in t[::-1]])


def test_never_rasterizes(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("the polygon profile must not rasterize")
    monkeypatch.setattr(s6, "build_shape_field", boom)
    monkeypatch.setattr(s6, "_rasterize", boom)
    assert pp.profile_stats(BAR) is not None


@pytest.mark.parametrize("variant", ["profile", "profile:raw"])
@pytest.mark.parametrize("name,poly", [("BAR", BAR), ("O_RING", O_RING),
                                       ("C_STROKE", C_STROKE), ("T_SHAPE", T_SHAPE)])
def test_letterform_archetypes_keep_satin(variant, name, poly):
    v = rs.classify_variant(poly, variant, "flat")
    assert v.satin and v.reason == "satin", (name, v.reason, v.metrics)


@pytest.mark.parametrize("variant", ["profile", "profile:raw"])
@pytest.mark.parametrize("tooth", [0.3, 0.6, 1.2])
def test_the_serrated_disc_stays_refused(variant, tooth):
    v = rs.classify_variant(_serrated_disc(10.0, tooth), variant, "gradient")
    assert not v.satin, (tooth, v.reason, v.metrics)


def test_a_square_corner_twig_counts_like_the_raster():
    """Weighted, not pruned: the bar's corner twigs count at cos(45 deg), so
    the spine reads ~26 mm like the raster's, not the 22 mm a pruned axis
    reads (with cv 0, which is how pruning lost the blob detector)."""
    pro, ras = pp.profile_stats(BAR, floor_px=0.0), s6._dt_stats(BAR)
    assert abs(pro.spine_len_mm - ras.spine_len_mm) < 1.0
    assert abs(pro.std / pro.mean - ras.std / ras.mean) < 0.05


def test_more_vertices_on_the_same_curve_barely_move_it():
    """The property the construction was built for: the same ribbon drawn
    with more boundary detail reads the same numbers (it does; what failed
    was agreement with the shipped verdicts, see the doc)."""
    def spread(reads):
        cv = [r.std / r.mean for r in reads]
        ex = [r.explained for r in reads]
        return max(cv) - min(cv), max(ex) - min(ex)

    # From 48 vertices up; under that the faceted arc really is a different
    # shape and both readings move with it (measured 2026-11-06: raster cv
    # spread 0.026 at 48-384 vertices, profile 0.009, raw profile 0.004).
    polys = [_arc(n) for n in (48, 96, 192, 384)]
    ras = spread([s6._dt_stats(p) for p in polys])
    for floor in (0.0, 1.0):
        pro = spread([pp.profile_stats(p, floor_px=floor) for p in polys])
        assert pro[0] < 0.01 and pro[0] < ras[0], (floor, pro, ras)
        assert pro[1] < 0.015 and pro[1] < ras[1], (floor, pro, ras)


def test_a_blob_is_not_elongated():
    blob = Point(0, 0).buffer(3.0, quad_segs=16).intersection(box(-3, -1.2, 3, 1.2))
    assert pp.profile_stats(blob).elongation < s6._PROMOTE_ELONGATION_MIN


def test_degenerate_shapes_defer():
    assert pp.profile_stats(Polygon()) is None
