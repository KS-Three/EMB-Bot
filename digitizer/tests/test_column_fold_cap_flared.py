"""`cfg.lettering_columns_corner_fold_cap_flared` (2026-11-14, built OFF as a `cfg.extra` key; ON since
2026-11-15, Kent's flip): a gate on the corner fold, read off the pro's files
(`docs/apex-pro-construction-2026-11-14.md`, section 6). He caps a corner
whose outline carries a flare (MARINE's E and R at the top-left) and fans a
plain one (MARINE's E at the bottom-left, every L of ProSeal's italic
PROSEAL). ON, a flared top corner is cut level across the stem at the arm's
lower edge (`outline_cut._cap_flared_cuts`), and `_fold_corners` leaves that
corner alone.
"""
from __future__ import annotations

from dataclasses import replace

from shapely.geometry import Point, Polygon

from digitizer_core import PipelineConfig, pipeline
from digitizer_core import outline_cut as oc

#: a slab-serif E's left side: a wedge at the top-left (MARINE), square below
FLARED_L = Polygon([(1.0, 0.0), (10.0, 0.0), (10.0, 4.0), (5.0, 4.0), (5.0, 12.0),
                    (0.8, 12.0), (0.8, 5.0), (0.0, 2.5)])
#: the same L without the wedge
PLAIN_L = Polygon([(1.0, 0.0), (10.0, 0.0), (10.0, 4.0), (5.0, 4.0), (5.0, 12.0),
                   (1.0, 12.0)])
#: an italic L's top-left: the stem slants and never comes back
ITALIC_L = Polygon([(2.0, 0.0), (11.0, 0.0), (10.5, 4.0), (5.5, 4.0), (4.0, 12.0),
                    (0.0, 12.0)])


def _cut(poly, on: bool):
    with oc.fold_cap_flared_scope(on):
        return oc.letter_columns(poly, 0.4, fold_cuts=True, mitre_ends=True, rail_axis=True,
                                 corner_fold=True)


def test_the_scope_is_off_by_default_and_puts_itself_back():
    assert oc._FOLD_CAP_FLARED.get() is False
    with oc.fold_cap_flared_scope(True):
        assert oc._FOLD_CAP_FLARED.get() is True
    assert oc._FOLD_CAP_FLARED.get() is False


def test_plan_stitches_sets_it_from_the_field_for_its_own_plan_only(monkeypatch):
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: oc._FOLD_CAP_FLARED.get())
    assert pipeline.plan_stitches(None, PipelineConfig()) is False     # OFF again since 2026-11-17 (Kent's revert)
    on = replace(PipelineConfig(), lettering_columns_corner_fold_cap_flared=True)
    assert pipeline.plan_stitches(None, on) is True
    assert oc._FOLD_CAP_FLARED.get() is False


def test_the_flare_test_reads_a_wedge_not_a_square_or_italic_corner():
    W = 4.0
    assert oc._flared(FLARED_L, (1.0, 0.0), W)
    assert not oc._flared(PLAIN_L, (1.0, 0.0), W)
    assert not oc._flared(ITALIC_L, (2.0, 0.0), W)


def test_plain_and_italic_corners_cut_as_off():
    for poly in (PLAIN_L, ITALIC_L):
        a, b = _cut(poly, True), _cut(poly, False)
        assert a.cuts == b.cuts and [c.stations for c in a.columns] == [c.stations for c in b.columns]


def test_a_flared_corner_is_capped_level_and_not_folded():
    lc = _cut(FLARED_L, True)
    caps = [c for c in lc.cuts if c[2] == "corner_cap"]
    assert len(caps) == 1
    (a, b, _r, _L) = caps[0]
    assert abs(a[1] - b[1]) < 1e-6 and abs(a[1] - 4.0) < 0.05      # the arm's lower edge, level
    # the arm's piece takes the stem's top: one column over the corner and the arm
    corner, arm = Point(1.5, 1.0), Point(8.0, 2.0)
    cap = [c for c in lc.columns if c.piece.distance(corner) < 1e-6]
    assert len(cap) == 1 and cap[0].piece.distance(arm) < 1e-6
    assert "fold" not in [c[2] for c in lc.cuts]
