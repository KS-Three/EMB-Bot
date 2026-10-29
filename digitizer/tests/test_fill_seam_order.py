"""`cfg.fill_seam_order` (built OFF 2026-10-29): a fill's sections sewn as one
continuous tatami (`stage6_fill._order_for_seams`).

The top pink line Kent circled on the Instagram icon at 80 mm is no travel: it is
the seam where a fill section sewn LATE ends on the edge row of a section sewn
early (the band split at the dot's top tangent), the one row in the band nothing
covers. ON, every section of the fill progresses the same way across its rows and
starts only once each section it shares a seam with upstream is sewn. Instagram:
ridge seams 8 -> 0, direction flips 19 -> 5 (all in the white under-fill), trims
23 -> 24 (26 with `fill_bridge_cut_exposed`).
"""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core import PipelineConfig
from digitizer_core.stage6_fill import (_order_for_seams, _section_rows, _seam_side, _uv,
                                        seam_order_scope, stitch_shape)

ROW = 0.4
# A plate with a hole in its middle: the rows split round the hole into a section
# above, two beside it and one below, each pair sharing a seam along a row.
PLATE = box(0, 0, 40, 30).difference(box(15, 10, 25, 20))


def _rows_of(y0, y1, x0=0.0, x1=10.0):
    """A zigzag section of horizontal rows from y0 to y1 (exclusive), ROW apart."""
    path, y, k = [], y0, 0
    while y < y1 - 1e-9:
        row = [(x0, y), (x1, y)] if k % 2 == 0 else [(x1, y), (x0, y)]
        path.extend(row)
        y += ROW
        k += 1
    return path


def test_default_is_off():
    assert PipelineConfig().fill_seam_order is False


def test_a_seam_is_read_on_any_row_not_only_the_extremes():
    a = _rows_of(0.0, 4.0)
    b = _rows_of(4.0, 8.0)
    assert _seam_side(_section_rows(a, 0.0), _section_rows(b, 0.0), ROW) == 1
    assert _seam_side(_section_rows(b, 0.0), _section_rows(a, 0.0), ROW) == -1


def test_side_by_side_sections_share_no_seam():
    a = _rows_of(0.0, 4.0, 0.0, 10.0)
    b = _rows_of(0.0, 4.0, 20.0, 30.0)
    assert _seam_side(_section_rows(a, 0.0), _section_rows(b, 0.0), ROW) == 0


def test_the_upstream_section_goes_first_and_every_section_goes_one_way():
    # handed in the order that made the Instagram ridge: the lower one first,
    # the upper one last and ending on it
    lower = _rows_of(4.0, 8.0)
    upper = _rows_of(0.0, 4.0)
    out = _order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW)
    assert len(out) == 2
    (v0, v1) = (_uv(out[0][0], 0.0)[1], _uv(out[0][-1], 0.0)[1])
    (w0, w1) = (_uv(out[1][0], 0.0)[1], _uv(out[1][-1], 0.0)[1])
    assert (v1 - v0) * (w1 - w0) > 0, "the two sections progress opposite ways"
    # the later section starts at the seam the earlier one finished on
    assert abs(out[1][0][1] - out[0][-1][1]) <= 1.0


def _seam_report(runs, angle=0.0):
    fills = [r for r in runs if r.kind == "fill" and len(r.points) > 4]
    rows = [_section_rows(r.points, angle) for r in fills]
    dirs = [1 if _uv(r.points[-1], angle)[1] > _uv(r.points[0], angle)[1] else -1 for r in fills]
    ridge = flip = 0
    for a in range(len(fills)):
        for b in range(a + 1, len(fills)):
            side = _seam_side(rows[a], rows[b], ROW)
            if side == 0:
                continue
            if dirs[a] != dirs[b]:
                flip += 1
            elif side != dirs[a]:
                ridge += 1
    return len(fills), ridge, flip


def _sew():
    runs, _ = stitch_shape(PLATE, "P", angle_deg=0.0, row_mm=ROW, stitch_mm=3.0,
                           underlay_style="none", trim_at_mm=3.0, start_near=(40.0, 30.0))
    return runs


def test_on_the_plate_sews_no_ridge_and_no_flip():
    with seam_order_scope(True):
        n, ridge, flip = _seam_report(_sew())
    assert n >= 3
    assert ridge == 0 and flip == 0


def test_on_moves_the_plate_and_off_restores_it():
    off = [(r.kind, r.points) for r in _sew()]
    with seam_order_scope(True):
        on = [(r.kind, r.points) for r in _sew()]
    again = [(r.kind, r.points) for r in _sew()]
    assert again == off
    assert sorted(p for k, pts in on if k == "fill" for p in pts) == \
        sorted(p for k, pts in off if k == "fill" for p in pts), "the same rows, reordered"


def test_the_pipeline_scopes_the_flag():
    import inspect
    from digitizer_core import pipeline
    assert "seam_order_scope(cfg.fill_seam_order)" in inspect.getsource(pipeline.plan_stitches)
