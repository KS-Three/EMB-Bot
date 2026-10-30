"""`cfg.fill_bridge_cut_exposed` (built OFF 2026-10-29): a fill bridge that shows on
finished fill is cut whatever `_score` says.

`fill_bridge_cut` cuts a bridge only when `_score` prices it dearer than the
cut (25 stitches a trim, 2x per exposed stitch), so a 9 mm line across a band's
own finished rows -- about 11 at that rate -- stays sewn. Kent circled exactly
those lines on the Instagram icon at 80 mm (2026-10-29): the gold vertical, the
yellow line under the ring, the orange diagonal, the pink line left of the
ring. ON, any bridge whose exposure clears the tolerance and whose gap is over
`trim_at_mm` is lifted and cut; a hidden bridge and a gap under `trim_at_mm`
are left as they were. Instagram at 80 mm: exposed travel 53.0 -> 0.4 mm
(`tools/travel_legs.py`'s exact reading), trims 23 -> 31.
"""
from __future__ import annotations

from shapely.geometry import box

from digitizer_core import PipelineConfig, machine
from digitizer_core.stage6_fill import (_cut_is_cheaper, _densify, _reorder_key,
                                        cut_exposed_scope)

from .test_fill_bridge_cut import TRIM_AT

SEWN = box(0, 0, 100, 10)


def _bridge(a, b):
    return _densify(a, b, machine.TRAVEL_STITCH_MM)


def test_default_is_off():
    assert PipelineConfig().fill_bridge_cut_exposed is False


def test_off_a_short_exposed_bridge_is_cheaper_than_the_cut():
    # 8 mm on finished fill: under the scorer's 25 for a trim, so it is sewn
    a, b = (1.0, 5.0), (9.0, 5.0)
    assert not _cut_is_cheaper(a, _bridge(a, b), SEWN, TRIM_AT)


def test_on_the_same_bridge_is_cut():
    a, b = (1.0, 5.0), (9.0, 5.0)
    with cut_exposed_scope(True):
        assert _cut_is_cheaper(a, _bridge(a, b), SEWN, TRIM_AT)


def test_on_a_hidden_bridge_is_still_sewn():
    a, b = (1.0, 5.0), (41.0, 5.0)
    with cut_exposed_scope(True):
        assert not _cut_is_cheaper(a, _bridge(a, b), box(0, 50, 100, 60), TRIM_AT)
        assert not _cut_is_cheaper(a, _bridge(a, b), None, TRIM_AT)


def test_on_a_gap_under_trim_at_is_left_alone():
    a, b = (1.0, 5.0), (3.5, 5.0)
    with cut_exposed_scope(True):
        assert not _cut_is_cheaper(a, _bridge(a, b), SEWN, TRIM_AT)


def test_the_scope_resets():
    a, b = (1.0, 5.0), (9.0, 5.0)
    with cut_exposed_scope(True):
        pass
    assert not _cut_is_cheaper(a, _bridge(a, b), SEWN, TRIM_AT)


def test_the_scope_is_part_of_the_reorder_memo_key():
    args = (b"t", [[(0.0, 0.0), (1.0, 0.0)]], box(0, 0, 1, 1), None, None, None, 1.0)
    off = _reorder_key(*args)
    with cut_exposed_scope(True):
        on = _reorder_key(*args)
    assert off != on


def test_the_pipeline_scopes_the_flag():
    from digitizer_core import pipeline
    import inspect
    assert "cut_exposed_scope(cfg.fill_bridge_cut_exposed)" in inspect.getsource(pipeline.plan_stitches)


# --- a satin rim's lead-in (stage6_border.border_runs) ----------------------
# flat_emoji_icon at 80 mm (2026-10-30): with `fill_seam_order` the horn's fill
# ended mid-shape and its rim's lead-in was a 7 mm line across the finished
# horn. ON, the lead-in rides only the band the rim is still to sew, or lifts.

def _rim(entry):
    from digitizer_core.stage6_border import border_runs
    from digitizer_core import stitches
    runs, report = border_runs(box(0, 0, 30, 30), "S1", entry=entry, trim_at_mm=TRIM_AT)
    travel = sum(len(r.points) for r in runs if r.kind == stitches.TRAVEL)
    return runs, report, travel


def test_off_a_rim_lead_in_crosses_the_finished_fill():
    _, report, travel = _rim((15.0, 15.0))
    assert travel > 0 and report["cut_exposed"] == 0


def test_on_a_rim_lead_in_across_the_fill_is_lifted():
    with cut_exposed_scope(True):
        runs, report, travel = _rim((15.0, 15.0))
    assert travel == 0 and report["cut_exposed"] == 1
    assert runs[0].jump and runs[0].trim


def test_on_a_rim_lead_in_from_the_edge_is_unchanged():
    off = _rim((0.0, 15.0))
    with cut_exposed_scope(True):
        on = _rim((0.0, 15.0))
    assert on[1]["cut_exposed"] == 0
    assert [r.points for r in on[0]] == [r.points for r in off[0]]
