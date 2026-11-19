"""`cfg.outline_strip_column` (built OFF 2026-11-19): `digitizer_core/outline_strip.py`."""
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, stitches
from digitizer_core.outline_strip import strip_column_runs, strip_pieces

W = 1.88       # MFab's loop width at 104.9 mm


def band(gap: float) -> tuple[Polygon, list]:
    """A 3 mm band round two 8 x 6 mm holes standing `gap` apart."""
    h1 = box(0, 0, 8, 6)
    h2 = box(8 + gap, 0, 16 + gap, 6)
    outer = box(-3, -3, 19 + gap, 9)
    art = Polygon(outer.exterior.coords, [h1.exterior.coords, h2.exterior.coords])
    return art, [(h1, W), (h2, W)]


def test_default_is_off():
    assert PipelineConfig().outline_strip_column is False


def test_a_strip_between_two_holes_is_found():
    art, rings = band(3.0)
    strips = strip_pieces(art, rings)
    assert len(strips) == 1
    s = strips[0]
    assert abs(s.centroid.x - 9.5) < 0.1                 # the 3 mm between the holes
    mid = s.intersection(box(0, 1, 20, 5))               # away from the corners
    assert abs(mid.bounds[0] - 8.0) < 0.1 and abs(mid.bounds[2] - 11.0) < 0.1
    assert s.bounds[3] - s.bounds[1] >= 6.0 * 0.9        # most of the 6 mm stem


def test_a_hairline_stem_is_left_to_the_loops():
    """BECKER's stems between letters are 0.55-1.1 mm: under one loop width."""
    art, rings = band(1.0)
    assert strip_pieces(art, rings) == []


def test_a_strip_wider_than_two_loops_is_not_a_strip():
    art, rings = band(4.5)
    assert strip_pieces(art, rings) == []


def test_runs_are_the_loops_then_one_column():
    art, rings = band(3.0)
    runs, rep = strip_column_runs(
        art, rings, "S", reach=art, entry=(-3, -3), trim_at_mm=2.0, underlay=False,
        satin_kw={"underlay_style": "none", "trim_at_mm": 2.0}, loop_kw={})
    assert not rep["empty"] and rep["strips"] == 1 and rep["loops"] == 2
    satin = [r for r in runs if r.kind == stitches.SATIN]
    last = satin[-1]
    xs = [p[0] for p in last.points]
    assert min(xs) > 7.0 and max(xs) < 12.0               # the column sits on the strip
    # its crosses span the strip, not a loop width
    span = max(abs(a[0] - b[0]) for a, b in zip(last.points, last.points[1:]))
    assert span > 2.5
