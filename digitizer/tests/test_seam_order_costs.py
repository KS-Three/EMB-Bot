"""`cfg.fill_seam_order_priced` and `cfg.knockdown_shorter_walk` (built OFF
2026-10-30): two costs `fill_seam_order` carries, each with its own switch.

- Priced: seam order picked between its two progressions on the flown chord,
  which cannot see a section walled in behind finished fill. ON, the one with
  fewer ridges and flips sews, and `_score` settles a tie between them.
- Knockdown: the beanie's knockdown never lifts (`knockdown._stay_down`), so a
  hop seam order adds is sewn: Becker beanie's walk 38.7 -> 77.9 mm, ProSeal
  beanie's shorter. ON, both are sewn and the shorter walk kept.

`docs/seam-order-attribution-2026-10-30.md` has the measurements.
"""
from __future__ import annotations

import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, knockdown, stage6_fill, stitches
from digitizer_core.stage6_fill import (_SEAM_ORDER, _SEAM_PRICED, _order_for_seams, _section_rows,
                                        _seam_side, _uv, seam_order_held, seam_order_scope,
                                        seam_priced_scope, stitch_shape)
from digitizer_core.stitches import StitchRun
from tests.test_fill_seam_order import PLATE, ROW, _rows_of

KHAKI = (195, 176, 145)


def test_both_switches_are_on_by_default():
    cfg = PipelineConfig()    # Kent 2026-10-30, "Flip ON (Recommended)" on each
    assert cfg.fill_seam_order_priced is True
    assert cfg.knockdown_shorter_walk is True
    assert not _SEAM_PRICED.get()      # set for the length of one plan


def test_plan_stitches_reads_the_priced_flag(monkeypatch):
    from digitizer_core import pipeline
    seen = []
    monkeypatch.setattr(pipeline, "_plan_stitches", lambda result, cfg: seen.append(_SEAM_PRICED.get()))
    pipeline.plan_stitches(None, PipelineConfig(fill_seam_order_priced=False))
    pipeline.plan_stitches(None, PipelineConfig())
    assert seen == [False, True]
    assert not _SEAM_PRICED.get()


def test_the_price_decides_where_the_chord_would_not():
    """Two valid progressions. Entered nearer one end, the chord picks that one;
    a price against it picks the other, and it still obeys the seam."""
    lower, upper = _rows_of(4.0, 8.0), _rows_of(0.0, 4.0)
    by_chord = _order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW)
    first = _uv(by_chord[0][0], 0.0)[1]
    priced = _order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW,
                              lambda order: 0.0 if _uv(order[0][0], 0.0)[1] != first else 1.0)
    assert _uv(priced[0][0], 0.0)[1] != first
    (v0, v1) = (_uv(priced[0][0], 0.0)[1], _uv(priced[0][-1], 0.0)[1])
    (w0, w1) = (_uv(priced[1][0], 0.0)[1], _uv(priced[1][-1], 0.0)[1])
    assert (v1 - v0) * (w1 - w0) > 0, "the priced order broke the one progression"
    assert _seam_side(_section_rows(priced[0], 0.0), _section_rows(priced[1], 0.0), ROW) != 0


def test_the_lay_comes_before_the_price(monkeypatch):
    """Becker beanie: the cheaper progression had 6 flips, the chord's 0. A price
    never buys a worse lay, and is not even asked for when the lays differ."""
    lower, upper = _rows_of(4.0, 8.0), _rows_of(0.0, 4.0)
    chord = _order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW)
    first = _uv(chord[0][0], 0.0)[1]
    real = stage6_fill._seam_faults
    monkeypatch.setattr(stage6_fill, "_seam_faults",
                        lambda order, *a: 0 if _uv(order[0][0], 0.0)[1] == first else 3)

    def boom(_order):
        raise AssertionError("priced two progressions that do not lay alike")
    assert _order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW, boom) == chord
    assert real(chord, 0.0, ROW) == 0


def test_seam_faults_reads_a_ridge_and_a_flip():
    lower, upper = _rows_of(4.0, 8.0), _rows_of(0.0, 4.0)
    assert stage6_fill._seam_faults([upper, lower], 0.0, ROW) == 0   # one tatami, top down
    assert stage6_fill._seam_faults([lower, upper], 0.0, ROW) == 1   # ends on the early edge row
    assert stage6_fill._seam_faults([upper, lower[::-1]], 0.0, ROW) == 1   # a flip


def test_a_tied_price_falls_back_to_the_chord():
    lower, upper = _rows_of(4.0, 8.0), _rows_of(0.0, 4.0)
    assert (_order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW, lambda _o: 7.0)
            == _order_for_seams([lower, upper], 0.0, (0.0, 0.0), ROW))


def _sew(under_cover: bool):
    return stitch_shape(PLATE, "P", angle_deg=0.0, row_mm=ROW, stitch_mm=3.0,
                        underlay_style="none", trim_at_mm=3.0, start_near=(40.0, 30.0),
                        under_cover=under_cover, cut_bridges=under_cover)[0]


def _rows(runs):
    return [(r.kind, r.jump, r.trim, list(r.points)) for r in runs]


def test_the_price_runs_only_under_cover(monkeypatch):
    """Without the footprint `_order_cost` has nothing to price exposure with;
    such a shape (the knockdown, a blend band) stays on the chord."""
    with seam_order_scope(True):
        chord = _rows(_sew(False))
        with seam_priced_scope(True):
            assert _rows(_sew(False)) == chord


def test_the_scope_is_off_outside_a_plan():
    with seam_order_scope(True):
        assert _SEAM_ORDER.get()
        with seam_order_held(False):
            assert _SEAM_ORDER.get()
        with seam_order_held(True):
            assert not _SEAM_ORDER.get()
        assert _SEAM_ORDER.get()


def _kd_cfg(**kw):
    return PipelineConfig(garment_id="beanie", garment_rgb=KHAKI, **kw)


def _fill(x0: float) -> StitchRun:
    return StitchRun(points=[(x0, 0.0), (x0 + 1.0, 0.0)], kind=stitches.FILL,
                     shape_id=knockdown.SHAPE_ID)


def _sewing(walk_mm: float) -> list[StitchRun]:
    """A fill, a walk of `walk_mm`, a fill."""
    walk = StitchRun(points=[(1.0 + walk_mm, 0.0)], kind=stitches.TRAVEL,
                     shape_id=knockdown.SHAPE_ID)
    return [_fill(0.0), walk, _fill(1.0 + walk_mm)]


def test_walk_mm_counts_from_the_stitch_before_the_walk():
    assert knockdown._walk_mm(_sewing(38.7)) == pytest.approx(38.7)
    assert knockdown._walk_mm([_fill(0.0)]) == 0.0


def _knockdown_with(monkeypatch, cfg, seam_walk, held_walk):
    """The block when the seam-ordered sewing walks `seam_walk` and the held one
    `held_walk`, and which arms `_sewn` was asked for."""
    asked = []

    def sewn(_poly, _here, _trim, hold_seams=False):
        asked.append(hold_seams)
        return _sewing(held_walk if hold_seams else seam_walk)
    monkeypatch.setattr(knockdown, "_sewn", sewn)
    block, _report = knockdown.knockdown_block([box(0, 0, 30, 12)], cfg, 3.0)
    assert block is not None
    return block, asked


def test_off_sews_the_knockdown_once_with_seam_order(monkeypatch):
    block, asked = _knockdown_with(monkeypatch, _kd_cfg(knockdown_shorter_walk=False), 77.9, 38.7)
    assert asked == [False]
    assert knockdown._walk_mm(block.runs) == pytest.approx(77.9, abs=1.0)


@pytest.mark.parametrize("seam,held,want", [(77.9, 38.7, 38.7), (40.0, 90.0, 40.0)])
def test_on_keeps_the_shorter_walk_either_way(monkeypatch, seam, held, want):
    """Becker beanie is the first row, ProSeal beanie's direction the second."""
    block, asked = _knockdown_with(monkeypatch, _kd_cfg(), seam, held)
    assert asked == [False, True]
    assert knockdown._walk_mm(block.runs) == pytest.approx(want, abs=1.0)


def test_sewn_holds_seam_order_only_when_asked(monkeypatch):
    seen = []
    real = knockdown.stitch_shape

    def spy(*a, **k):
        seen.append(_SEAM_ORDER.get())
        return real(*a, **k)
    monkeypatch.setattr(knockdown, "stitch_shape", spy)
    with seam_order_scope(True):
        knockdown._sewn(box(0, 0, 30, 12), None, 3.0)
        knockdown._sewn(box(0, 0, 30, 12), None, 3.0, hold_seams=True)
    assert seen == [True, False]
    assert stage6_fill._SEAM_ORDER.get() is False


def test_off_is_the_engine_as_it_was():
    """Both switches OFF the shape is sewn by `_order_for_seams`' chord: the same
    call with `price=None`, and an unset priced scope changes nothing."""
    with seam_order_scope(True):
        off = _rows(_sew(True))
        with seam_priced_scope(False):
            assert _rows(_sew(True)) == off
