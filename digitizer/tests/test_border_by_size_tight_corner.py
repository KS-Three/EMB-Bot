"""The size ring keeps a near-sharp corner (`cfg.border_by_size_tight_corner`, built OFF 2026-11-17).

The size ring (`border_by_size`) is built on the shape with every corner
relaxed inward by `BORDER_CORNER_RADIUS_MM` (2.1 mm), so the sewn silhouette
of a flat square is a cushion and block letters read bevelled. The pro's ring
leaves its outer needle points almost at the corner (median equivalent radius
0.47 mm on 13 corners of one artwork). ON, only a BY-SIZE ring is built on
`machine.BORDER_BY_SIZE_CORNER_RADIUS_MM` (0.5 mm). Off, byte-identical.

Synthetic shapes only: the logo is not in the repo.
"""
from __future__ import annotations

import hashlib
import math
import statistics

from shapely.geometry import Point, Polygon, box

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.fabrics import fabric_for_garment
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import PlannedRegion
from digitizer_core.stage6_border import border_runs
from digitizer_core.stage7_sequence import sequence

ON = dict(border_by_size_tight_corner=True)
OFF = dict(border_by_size_tight_corner=False)


def _region(poly, sid="Sbig", **meta):
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="4101",
                  area_mm2=poly.area, source="test", meta={"layer": 0, **meta})


def _plan(poly, **cfg_kw):
    reg = _region(poly)
    planned = [PlannedRegion(region=reg, polygon=poly, sew_index=0)]
    blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                          PipelineConfig(underlay=False, **cfg_kw))
    return [r for b in blocks for r in b.runs]


def _md5(runs):
    h = hashlib.md5()
    for r in runs:
        h.update(r.kind.encode())
        for x, y in r.points:
            h.update(f"{x:.4f},{y:.4f};".encode())
    return h.hexdigest()


def _border_points(runs):
    return [p for r in runs if r.kind == stitches.BORDER for p in r.points]


def _corner_gap(runs):
    """Nearest the ring's needle points come to the square's (0, 0) corner."""
    return min(math.hypot(x, y) for x, y in _border_points(runs))


def _crosses(runs):
    out = []
    for r in runs:
        if r.kind != stitches.BORDER:
            continue
        for a, b in zip(r.points, r.points[1:]):
            out.append((math.hypot(b[0] - a[0], b[1] - a[1]),
                        ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)))
    return out


def test_flag_default_is_off():
    assert PipelineConfig().border_by_size_tight_corner is False


def test_the_constant_is_the_measured_pro_corner():
    # pro median 0.47 mm over 13 Becker corners, ours at 2.1 reads 2.32
    assert machine.BORDER_BY_SIZE_CORNER_RADIUS_MM == 0.5
    assert machine.BORDER_BY_SIZE_CORNER_RADIUS_MM < machine.BORDER_CORNER_RADIUS_MM


def test_on_a_12mm_sharp_square_the_ring_reaches_the_corner():
    sq = box(0, 0, 12, 12)
    off, on = _plan(sq, **OFF), _plan(sq, **ON)
    assert stitches.BORDER in [r.kind for r in on]
    # OFF the needle points sit about a millimetre in; ON within the 0.5 mm radius
    assert _corner_gap(off) > 0.8
    assert _corner_gap(on) < machine.BORDER_BY_SIZE_CORNER_RADIUS_MM


def test_on_the_ring_width_at_the_corner_holds():
    sq = box(0, 0, 12, 12)

    def widths(runs):
        segs = _crosses(runs)
        straight = [w for w, m in segs
                    if min(m) < 3 and 4 < max(m) < 8 and w > 1.0]
        corner = [w for w, m in segs if math.hypot(*m) < 2.5 and w > 1.0]
        return statistics.median(straight), statistics.median(corner)

    s_on, c_on = widths(_plan(sq, **ON))
    s_off, c_off = widths(_plan(sq, **OFF))
    assert abs(c_on - s_on) <= 0.15 * s_on
    assert c_off < 0.85 * s_off          # OFF pinches at the corner, as today


def test_on_an_l_shape_and_a_star_stay_clean():
    star = Polygon([(10 + (12 if i % 2 == 0 else 5) * math.cos(i * math.pi / 5),
                     10 + (12 if i % 2 == 0 else 5) * math.sin(i * math.pi / 5))
                    for i in range(10)])
    ell = Polygon([(0, 0), (20, 0), (20, 8), (8, 8), (8, 20), (0, 20)])
    for poly in (ell, star):
        off, on = _plan(poly, **OFF), _plan(poly, **ON)
        assert stitches.BORDER in [r.kind for r in on]
        w_off = [w for w, _ in _crosses(off)]
        w_on = [w for w, _ in _crosses(on)]
        # no new pinched or oversized cross at a convex or reflex corner
        assert min(w_on) >= min(w_off) - 1e-6
        assert max(w_on) <= max(w_off) + 0.05


def test_on_a_12mm_disc_is_byte_identical():
    disc = Point(0, 0).buffer(6.0, 64)
    off, on = _plan(disc, **OFF), _plan(disc, **ON)
    assert stitches.BORDER in [r.kind for r in off]
    assert _md5(off) == _md5(on)


def test_a_non_size_border_loop_is_byte_identical():
    # keyline / outline callers of `border_runs` pass no corner radius: the flag
    # does not reach them, and a corner_radius_mm of None is the old ring
    sq = box(0, 0, 12, 12)
    a, _ = border_runs(sq, "S1", entry=None, trim_at_mm=3.0, style="satin", width_mm=2.1)
    b, _ = border_runs(sq, "S1", entry=None, trim_at_mm=3.0, style="satin", width_mm=2.1,
                       corner_radius_mm=None)
    c, _ = border_runs(sq, "S1", entry=None, trim_at_mm=3.0, style="satin", width_mm=2.1,
                       corner_radius_mm=machine.BORDER_BY_SIZE_CORNER_RADIUS_MM)
    assert _md5(a) == _md5(b)
    assert _md5(a) != _md5(c)            # the argument is what moves it


def test_a_ring_the_user_asked_for_keeps_2p1_with_the_flag_on():
    # a per-shape border request is not a size ring: the flag leaves it alone
    sq = box(0, 0, 12, 12)
    reg = _region(sq, border="satin")
    planned = [PlannedRegion(region=reg, polygon=sq, sew_index=0)]
    out = []
    for kw in (OFF, ON):
        blocks, _w = sequence(planned, fabric_for_garment("hat_front"),
                              PipelineConfig(underlay=False, border_by_size=False, **kw))
        out.append(_md5([r for b in blocks for r in b.runs]))
    assert out[0] == out[1]


def test_corner_loss_still_refuses_an_8mm_sharp_square_with_the_flag_on():
    # the loss is read at 2.1 mm whatever the ring's own radius: Kent's ruling
    # 2026-11-17 on the flat square stands
    sq = box(0, 0, 8, 8)
    for kw in (OFF, ON):
        runs = _plan(sq, border_by_size_corner_loss=True, **kw)
        kinds = [r.kind for r in runs]
        assert stitches.FILL in kinds and stitches.BORDER not in kinds


def test_off_is_byte_identical_to_the_default_engine():
    sq = box(0, 0, 12, 12)
    assert _md5(_plan(sq, **OFF)) == _md5(_plan(sq))
