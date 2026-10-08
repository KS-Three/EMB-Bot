"""`cfg.fill_order_sewn_paths` (built OFF 2026-10-08): the fill column-order
scorer prices only the paths `emit` sews.

`_fill_paths` returns one-point "columns" at pointed tips and notches. `emit`
skips every one (`len(pts) < 2`), but `_order_cost` routed travel to each and
on from it, so both reorders chose a column order against bridges that are
never sewn. DOCTRINE (2026-09-11): "`_order_cost` and `emit` can disagree about
what an order will sew ... make those agree before trusting any order-level
guard". `tools/fill_score_agreement.py` found these phantoms are the only
disagreement on the nine logos at 80 mm.

The fixture is a shapely polygon on purpose, so a traced raster's platform
noise cannot move it: a comb of pointed teeth, filled at 30 degrees, gives
`_fill_paths` 54 paths of which 19 are one point.
"""
from __future__ import annotations

from shapely.geometry import LineString, Polygon

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.stage6_fill import (
    _EXPOSED_TOLERANCE_MM, _exposed_mm, _fill_paths, _inset_ring, _order_cost,
    _sewn_paths, clear_fill_reorder_memo, stitch_shape,
)
import digitizer_core.stage6_fill as sf

ROW, STITCH, TRIM_AT, ANGLE = 0.4, 3.0, 3.0, 30.0
_COMB = Polygon([(0, 0), (40, 0), (40, 4)]
                + sum([[(40 - 4 * k - 1, 20), (40 - 4 * k - 2, 4)] for k in range(9)], [])
                + [(0, 4)])


def _sew(flag: bool, monkeypatch=None, capture=None):
    clear_fill_reorder_memo()
    if capture is not None:
        real = sf._memoized

        def spy(key, compute):
            out = real(key, compute)
            capture[:] = [[list(p) for p in out]]
            return out
        monkeypatch.setattr(sf, "_memoized", spy)
    runs, _ = stitch_shape(_COMB, "S1", angle_deg=ANGLE, row_mm=ROW, stitch_mm=STITCH,
                           underlay_style="edge_run", trim_at_mm=TRIM_AT,
                           under_cover=True, cut_bridges=True, sewn_paths_only=flag)
    return runs


def _sewn_figures(runs):
    """(cuts, travel, exposed stitches) of the fill phase, read off the runs."""
    first = next(i for i, r in enumerate(runs) if r.kind == stitches.FILL)
    start = first
    while runs[start - 1].kind == stitches.TRAVEL:
        start -= 1
    cuts, travel, exposed, sewn = 0, 0, 0.0, None
    for i in range(start, len(runs)):
        r = runs[i]
        if r.kind == stitches.TRAVEL:
            travel += len(r.points)
            if sewn is not None:
                route = [runs[i - 1].points[-1]] + list(r.points) + [runs[i + 1].points[0]]
                exposed += max(0.0, _exposed_mm(route, sewn) - _EXPOSED_TOLERANCE_MM)
            continue
        if r.jump and r.trim:
            cuts += 1
        if r.kind == stitches.FILL and len(r.points) > 1:
            fp = LineString(r.points).simplify(ROW / 2.0).buffer(ROW)
            sewn = fp if sewn is None else sewn.union(fp)
    return cuts, float(travel), exposed / machine.TRAVEL_STITCH_MM


def _scored(runs, order):
    first = next(i for i, r in enumerate(runs) if r.kind == stitches.FILL)
    while runs[first - 1].kind == stitches.TRAVEL:
        first -= 1
    entry = runs[first - 1].points[-1]
    ring = _inset_ring(_COMB, machine.TRAVEL_INSET_MM)
    return _order_cost(order, _COMB, ring, _COMB.buffer(0.01), entry, TRIM_AT, ROW,
                       cut_bridges=True)


def _fill_points(runs):
    # Rounded: a reversed path can land a coordinate one float step away.
    return sorted((round(x, 9), round(y, 9))
                  for r in runs if r.kind == stitches.FILL for x, y in r.points)


def test_the_fixture_carries_phantom_columns():
    paths = _fill_paths(_COMB, ANGLE, ROW, STITCH, machine.FILL_STAGGERS, (0.0, 0.0))
    assert sum(len(p) < 2 for p in paths) >= 10
    assert _sewn_paths(paths) == [p for p in paths if len(p) >= 2]


def test_default_is_off_and_off_is_the_old_call():
    assert PipelineConfig().fill_order_sewn_paths is False
    clear_fill_reorder_memo()
    old, _ = stitch_shape(_COMB, "S1", angle_deg=ANGLE, row_mm=ROW, stitch_mm=STITCH,
                          underlay_style="edge_run", trim_at_mm=TRIM_AT,
                          under_cover=True, cut_bridges=True)
    new = _sew(False)
    assert [(r.kind, r.points, r.jump, r.trim) for r in old] == \
           [(r.kind, r.points, r.jump, r.trim) for r in new]


def test_off_the_scorer_prices_bridges_emit_never_sews(monkeypatch):
    order: list = []
    runs = _sew(False, monkeypatch, order)
    assert any(len(p) < 2 for p in order[0])
    assert _scored(runs, order[0]) != _sewn_figures(runs)


def test_on_the_scorer_and_the_emitter_agree(monkeypatch):
    order: list = []
    runs = _sew(True, monkeypatch, order)
    assert all(len(p) >= 2 for p in order[0])
    scored, sewn = _scored(runs, order[0]), _sewn_figures(runs)
    assert scored[0] == sewn[0] and scored[1] == sewn[1]
    assert abs(scored[2] - sewn[2]) < 1e-9


def test_on_sews_the_same_penetrations():
    assert _fill_points(_sew(True)) == _fill_points(_sew(False))


def test_the_config_reaches_every_fill_call_site():
    """Stage 7's five tatami calls and the blend tier's two pass the flag."""
    from pathlib import Path
    root = Path(sf.__file__).parent
    s7 = (root / "stage7_sequence.py").read_text()
    sb = (root / "stage6_blend.py").read_text()
    assert s7.count("sewn_paths_only=cfg.fill_order_sewn_paths") == \
        s7.count("cut_bridges=cfg.fill_bridge_cut") == 5
    assert sb.count("sewn_paths_only=cfg.fill_order_sewn_paths") == \
        sb.count("cut_bridges=cfg.fill_bridge_cut") == 2
