"""`run_soft_vertices` (built OFF): the run tier's curve vertices cut before
sampling, corners kept. MASTER_SCOPE defect 46 (Law 37's direction-change
score) is the number it moves."""
import math

from shapely.geometry import Polygon

from digitizer_core import curve_fidelity as cf
from digitizer_core.config import PipelineConfig
from digitizer_core.stage6_border import _soften_ring, run_outline


def _ngon(n, r=4.0):
    return [(r * math.cos(2 * math.pi * k / n), r * math.sin(2 * math.pi * k / n))
            for k in range(n)] + [(r, 0.0)]


def _roughness(poly, soft):
    runs, _ = run_outline(Polygon(poly), "s", entry=None, trim_at_mm=7.0,
                          soft_vertices=soft)
    return cf.measure([p for r in runs
                       for p in [__import__("numpy").asarray(r.points, float)]])["roughness_deg"]


def test_default_is_off():
    assert PipelineConfig().run_soft_vertices is False


def test_corners_are_kept_exactly():
    sq = [(0, 0), (10, 0), (10, 10), (0, 10), (0, 0)]
    assert _soften_ring(sq) == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]


def test_cut_stays_inside_the_tolerance():
    ring = _ngon(12)
    out = Polygon(_soften_ring(ring))
    assert Polygon(ring).exterior.hausdorff_distance(out.exterior) <= 0.2 + 1e-9


def test_polygonised_curve_reads_smoother():
    ring = _ngon(16)
    assert _roughness(ring, True) < _roughness(ring, False)
