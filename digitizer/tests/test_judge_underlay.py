"""The two built-OFF flags' sewn judges count underlay on bare cloth as spill.

`thread_cover_spill` reads satin and fill only, so an underlay chord laid
outside a letter, over cloth no satin reaches, was invisible to the "net"
rule that `lettering_columns_absorb_unsewn` (`columns.absorb_gains`) and
`lettering_columns_stroke_floor` (`columns._stroke_floor_judged`) judge by.
`columns.bare_underlay` measures it, and both judges add it to the spill.
`cfg.lettering_columns_cover_handback` (`handback_wins` without
`underlay`) keeps the plain measure.
"""
from shapely.geometry import box

from digitizer_core import columns as C
from digitizer_core.stitches import SATIN, UNDERLAY, StitchRun

from .test_absorb_unsewn import A_COAL, _sew as _sew_coal
from .test_stroke_floor import E_HAT, Y_BEYOND, _sew

SHAPE = box(0, 0, 10, 2)
BEFORE = [StitchRun(points=[(x, 0.2), (x, 1.8)], kind=SATIN) for x in (1, 3, 5)]
# one more satin column inside the shape, and an underlay stitch run out
# 3 mm over bare cloth beside it
CHORD = BEFORE + [StitchRun(points=[(7, 0.2), (7, 1.8)], kind=SATIN),
                  StitchRun(points=[(9, 1.0), (9, 5.0)], kind=UNDERLAY)]


def test_an_underlay_chord_over_bare_cloth_is_spill():
    gain = C.thread_cover_spill(CHORD, SHAPE)[0] - C.thread_cover_spill(BEFORE, SHAPE)[0]
    assert C.thread_cover_spill(CHORD, SHAPE)[1] == C.thread_cover_spill(BEFORE, SHAPE)[1] == 0.0
    assert C.bare_underlay(BEFORE, SHAPE) == 0.0
    assert C.bare_underlay(CHORD, SHAPE) > gain > 0            # 0.067 bare against 0.035 gained
    # satin and fill alone: more in, nothing more out -- the chord unseen
    assert C.handback_wins(BEFORE, CHORD, SHAPE, rule="net")
    # both flags' judges see it
    assert not C.handback_wins(BEFORE, CHORD, SHAPE, rule="net", underlay=True)
    assert not C.absorb_gains(BEFORE, CHORD, SHAPE)


def test_underlay_inside_the_letter_or_under_its_satin_is_not_counted():
    inside = BEFORE + [StitchRun(points=[(2, 0.5), (8, 1.5)], kind=UNDERLAY)]
    assert C.bare_underlay(inside, SHAPE) == 0.0
    # satin spilled past the shape with its underlay under it: the satin is
    # the spill, the underlay is hidden by it
    covered = BEFORE + [StitchRun(points=[(7, -3.0), (7, 5.0)], kind=UNDERLAY),
                        StitchRun(points=[(7, -3.0), (7, 5.0)], kind=SATIN)]
    assert C.bare_underlay(covered, SHAPE) == 0.0
    assert C.thread_cover_spill(covered, SHAPE)[1] > 0


def test_the_hat_e_is_refused_on_its_satin_not_its_underlay():
    # Commons Bukit's e at 85.1 mm hat. Main's own sew lays an underlay
    # chord across the e's mouth (0.74 mm outside the letter, 0.42 mm of it
    # bare); the floored sew lays one too, a little less bare. The new term
    # does not move the verdict: the floored satin spills more than it covers.
    kw = dict(pull_mm=0.4, text_lean_deg=12.7644)
    runs_off, _ = _sew(E_HAT, False, **kw)
    runs_raw, _ = _sew(E_HAT, True, judged=False, **kw)
    u_off, u_raw = C.bare_underlay(runs_off, E_HAT), C.bare_underlay(runs_raw, E_HAT)
    assert u_off > 0.03 and u_raw > 0.02                      # 0.046, 0.032: both chords seen
    assert u_raw < u_off
    assert not C.handback_wins(runs_off, runs_raw, E_HAT, rule="net")
    assert not C.handback_wins(runs_off, runs_raw, E_HAT, rule="net", underlay=True)


def test_the_beyond_y_still_wins():
    runs_off, _ = _sew(Y_BEYOND, False, text_lean_deg=14.8025)
    runs_on, rep_on = _sew(Y_BEYOND, True, text_lean_deg=14.8025)
    assert C.bare_underlay(runs_on, Y_BEYOND) < 1e-4 and C.bare_underlay(runs_off, Y_BEYOND) == 0.0
    assert C.handback_wins(runs_off, runs_on, Y_BEYOND, rule="net", underlay=True)
    assert rep_on["stroke_floor_kept"] == 1


def test_the_coal_a_still_wins():
    runs_off, _ = _sew_coal(absorb=False)
    runs_on, rep_on = _sew_coal(absorb=True)
    # its stem's underlay runs a little past the letter both ways (0.147, 0.149)
    assert C.bare_underlay(runs_on, A_COAL) - C.bare_underlay(runs_off, A_COAL) < 0.01
    assert C.absorb_gains(runs_off, runs_on, A_COAL)
    assert rep_on["absorbed"] == 2
