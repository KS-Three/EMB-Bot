"""`cfg.bean_letter_straight_mm` (built OFF 2026-10-20): a longer bean-letter
stitch on a straight stretch of spine (`stage6_beanletter._station_piece`).

Kent, Fremont 81 mm Hat, 2026-10-20: "1 is wiggly", "Eat Stay play are
wiggly". 0.45 mm 3-pass stitches lay a straight stem as a chain of beads.
Smoothing the spine first was measured the same day and moved nothing
visible. The longer stitch is a gate-1 candidate; the flip is Kent's.
"""
import math

from digitizer_core import PipelineConfig
from digitizer_core.stage6_beanletter import STRAIGHT_SAG_MM, _station_piece, bean_letter


def _gaps(pts):
    return [math.dist(a, b) for a, b in zip(pts, pts[1:])]


def _arc(r=0.8, n=80, sweep=math.pi):
    return [(r * math.cos(t), r * math.sin(t)) for t in (sweep * i / (n - 1) for i in range(n))]


def test_off_by_default():
    assert PipelineConfig().bean_letter_straight_mm is None


def test_a_straight_stem_takes_the_long_stitch():
    stem = [(0.0, y / 10) for y in range(31)]                     # 3 mm
    pts = _station_piece(stem, 0.45, 0.9)
    assert len(pts) == 5 and all(abs(g - 0.75) < 1e-9 for g in _gaps(pts))
    assert len(_station_piece(stem, 0.45, None)) == 8              # off: the short pitch


def test_a_tight_curve_keeps_the_short_stitch():
    bowl = _arc(r=0.4)                                              # a 9's bowl: 0.4 mm radius
    fine = _station_piece(bowl, 0.45, None)
    assert _station_piece(bowl, 0.45, 0.9) == fine


def test_a_gentle_curve_lengthens_only_as_far_as_the_sag_allows():
    from shapely.geometry import LineString
    arc = _arc(r=4.0, n=200, sweep=0.75)                            # 3 mm of a 4 mm radius
    pts = _station_piece(arc, 0.45, 0.9)
    assert 0.45 < max(_gaps(pts)) <= 0.9
    assert LineString(arc).hausdorff_distance(LineString(pts)) <= STRAIGHT_SAG_MM


def test_bean_letter_none_is_byte_identical_and_on_lays_fewer_stations():
    spines = [[(0.0, y / 10) for y in range(31)]]
    kw = dict(entry=None, trim_at_mm=3.0, stitch_mm=0.45)
    off, _ = bean_letter(spines, "S1", **kw)
    none, _ = bean_letter(spines, "S1", straight_mm=None, **kw)
    on, rep = bean_letter(spines, "S1", straight_mm=0.9, **kw)
    assert [r.points for r in off] == [r.points for r in none]
    assert not rep["empty"]
    assert len(on[0].points) < len(off[0].points)
