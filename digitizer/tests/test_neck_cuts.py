"""`cfg.extra["lettering_columns_neck_cuts"]` (built OFF 2026-11-17).

A heavy M at small size (US Forest Service shield at 80 mm, DEPARTMENT's M,
6.8 mm tall on 1.17 mm strokes): stems and diagonals run into one solid band
and the V's point hangs under it. The junction rules take no cut, the letter
splits once and each half sews along its stem: the point is bare and the M
reads as an H. ON, the two bay corners are joined to the notch (a neck), the
V sews as its own column, and the lane keeps that cut only if the letter
covers more of itself for it.
"""
from shapely.geometry import Point, Polygon

from digitizer_core import outline_cut as oc
from digitizer_core.columns import lettering_columns_shape, satin_cover

#: The M as the Column lane received it (plan mm, y down), to 0.001 mm.
HEAVY_M = Polygon([
    (-19.942, 24.55), (-20.842, 30.625), (-19.68, 30.815), (-19.742, 30.542), (-19.742, 30.375),
    (-19.697, 30.222), (-19.609, 29.556), (-19.529, 28.889), (-19.417, 28.188), (-18.917, 30.792),
    (-17.75, 28.537), (-17.683, 28.875), (-17.722, 29.208), (-17.793, 29.875), (-17.866, 30.45),
    (-17.968, 30.766), (-18.175, 31.156), (-17.929, 31.257), (-17.583, 31.327), (-17.351, 31.362),
    (-17.0, 31.375), (-16.175, 25.292), (-16.75, 25.071), (-17.443, 25.011), (-17.972, 26.264),
    (-18.284, 26.95), (-18.583, 27.458), (-18.917, 24.82), (-18.954, 24.761), (-19.166, 24.707),
    (-19.406, 24.664),
])
NOTCH = (-18.583, 27.458)

LANE_KW = dict(trim_at_mm=3.0, spacing_mm=0.4, pull_mm=0.3, pull_floor_mm=1.5,
               underlay_style="center_run", fold_cuts=True, square_ends=True, rail_axis=True,
               short_columns=True, corner_fold=True, corner_fold_apex_side=True,
               inside_stagger=True, inside_connectors=True, edge_walk=True)

#: A point well inside the V's hanging point, under the band.
V_POINT = Point(-18.75, 29.4)


def _sew(neck: bool):
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), oc.fold_cap_flared_scope(True), \
            oc.neck_cuts_scope(neck):
        return lettering_columns_shape(HEAVY_M, "M", **LANE_KW)


def _satin_reaches(runs, pt, within_mm=0.35):
    from shapely.geometry import LineString
    return any(LineString([a, b]).distance(pt) <= within_mm
               for r in runs if r.kind == "satin" for a, b in zip(r.points, r.points[1:]))


def test_the_junction_rules_take_no_cut_on_the_heavy_m():
    W = oc.stroke_width(HEAVY_M)
    cuts, reflex, _convex = oc.find_cuts(HEAVY_M, W)
    assert len(reflex) == 3 and cuts == []


def test_the_necks_join_both_bay_corners_to_the_notch():
    W = oc.stroke_width(HEAVY_M)
    _cuts, reflex, _convex = oc.find_cuts(HEAVY_M, W)
    necks = oc._neck_cuts(HEAVY_M, W, [], reflex)
    assert [c[2] for c in necks] == ["neck", "neck"]
    assert all(any(Point(e).distance(Point(NOTCH)) < 0.05 for e in (c[0], c[1])) for c in necks)
    assert all(c[3] <= oc.NECK_MAX_W * W for c in necks)


def test_a_corner_a_junction_cut_already_uses_takes_no_neck():
    W = oc.stroke_width(HEAVY_M)
    _cuts, reflex, _convex = oc.find_cuts(HEAVY_M, W)
    used = [(NOTCH, (-19.27, 28.94), "ext", 1.6)]
    necks = oc._neck_cuts(HEAVY_M, W, used, reflex)
    assert all(Point(e).distance(Point(NOTCH)) > 0.05 for c in necks for e in (c[0], c[1]))


def test_off_the_v_point_is_bare_and_on_it_is_sewn():
    off, _ = _sew(False)
    on, report = _sew(True)
    assert not _satin_reaches(off, V_POINT)
    assert _satin_reaches(on, V_POINT)
    assert report.get("neck_cuts") == 1
    assert satin_cover(on, HEAVY_M) > satin_cover(off, HEAVY_M)


def test_off_is_the_lane_as_it_was():
    """The scope unarmed and the scope never entered sew the same runs."""
    with oc.apex_pro_scope(True), oc.apex_pro_joints_scope(True), oc.fold_cap_flared_scope(True):
        plain, _ = lettering_columns_shape(HEAVY_M, "M", **LANE_KW)
    off, report = _sew(False)
    assert [r.points for r in off] == [r.points for r in plain]
    assert "neck_cuts" not in report


def test_a_letter_with_no_free_corner_pair_is_untouched():
    """A plain bar has no concave corner: armed, it sews as it does OFF."""
    bar = Polygon([(0, 0), (1.2, 0), (1.2, 6), (0, 6)])
    with oc.neck_cuts_scope(False):
        off, _ = lettering_columns_shape(bar, "I", **LANE_KW)
    with oc.neck_cuts_scope(True):
        on, report = lettering_columns_shape(bar, "I", **LANE_KW)
    assert [r.points for r in on] == [r.points for r in off]
    assert "neck_cuts" not in report


def test_flag_is_off_by_default():
    from digitizer_core import PipelineConfig
    assert not (PipelineConfig().extra or {}).get("lettering_columns_neck_cuts")
