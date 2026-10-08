"""`cfg.satin_tip_corner_gate` -- a tip must land on a convex corner.

Built OFF 2026-10-08 for MASTER_SCOPE defect 59 (Becker's N, M and E fanning
under `letterform_priors`). `_is_tip_end` reads only whether the boundary is
within `_TIP_REACH_HALVES` sewn half-widths along a junction end's tangent.
At a refit letter's sharp junction the NEIGHBOURING stroke's far edge is
(the N: 4.56-4.81 mm against a 4.84 mm reach), so the end is capped and
`_extend_to_cap` runs it through that stroke -- the fan.

ON, `_tip_lands_on_corner` also asks where the ray lands: a taper's apex
closes round the end (a convex corner of the outline), a meeting ends on a
neighbour's far wall (180 deg) or in a notch between strokes (over 180).
The census and the corpus price are in `docs/n-fan-cure-2026-10-08.md`.

The node's DEGREE, which `docs/n-fan-2026-10-07.md` named as the gate, was
measured first and refuted: every end the tip test is asked about on Becker
and ENTHUSIAST sits at a node of three or more arms (a node of two always
has an owner and a tuck, so never reaches the test), so a degree gate is
`satin_tip_caps=False` under another name.
"""
from __future__ import annotations

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6


def test_the_flag_is_off_by_default():
    """Built OFF: it moves junction ends on every logo, not only the fan
    letters, and trades coverage for the fan -- Kent's call on the render."""
    assert PipelineConfig().satin_tip_corner_gate is False
    assert PipelineConfig(satin_tip_corner_gate=True).satin_tip_corner_gate is True


def test_a_tapered_apex_is_a_corner():
    """A spine running up the middle of a 40-degree wedge, ending one
    half-width short of the apex: the ray lands on the apex, where the
    outline closes round the end -- a tip, and the gate keeps it."""
    wedge = Polygon([(0, 0), (4, 0), (2, 5.5)])
    spine = [(2.0, 1.0), (2.0, 4.0)]
    assert s6._is_tip_end(spine, wedge, 1.0, at_start=False)
    assert s6._tip_lands_on_corner(spine, wedge, 1.0, at_start=False)


def test_a_ray_through_a_neighbouring_stroke_lands_on_its_wall():
    """The N's lower node in miniature: an arm (the diagonal) ends at the
    left edge of a vertical stem 2.6 mm wide. Its ray crosses the stem and
    lands on the stem's far WALL -- inside reach, so `_is_tip_end` calls it
    a tip, but the outline is straight there (180 deg): a meeting."""
    stem_and_arm = Polygon([(0, 4), (5, 4), (5, 0), (7.6, 0), (7.6, 12),
                            (5, 12), (5, 6), (0, 6)])
    spine = [(1.0, 5.0), (5.0, 5.0)]
    assert s6._is_tip_end(spine, stem_and_arm, 1.75, at_start=False)
    assert not s6._tip_lands_on_corner(spine, stem_and_arm, 1.75, at_start=False)


def test_a_ray_into_a_notch_is_a_meeting():
    """The M's middle: an end aimed at the concave vertex of a V notch
    between two strokes. The outline turns AWAY from the ink there (the
    chord across the notch is outside the shape): a meeting, not a tip."""
    m_top = Polygon([(0, 0), (8, 0), (8, 6), (4, 3), (0, 6)])
    spine = [(4.0, 0.5), (4.0, 2.0)]
    assert s6._is_tip_end(spine, m_top, 1.0, at_start=False)
    assert not s6._tip_lands_on_corner(spine, m_top, 1.0, at_start=False)


def test_the_gate_reads_the_start_end_too_and_degenerate_spines_never_tip():
    wedge = Polygon([(0, 0), (4, 0), (2, 5.5)])
    assert s6._tip_lands_on_corner([(2.0, 4.0), (2.0, 1.0)], wedge, 1.0, at_start=True)
    assert not s6._tip_lands_on_corner([(2.0, 4.0), (2.0, 4.0)], wedge, 1.0, at_start=False)
    assert not s6._tip_lands_on_corner([(2.0, 4.0)], wedge, 1.0, at_start=False)
    assert not s6._tip_lands_on_corner([(2.0, 1.0), (2.0, 4.0)], wedge, 0.0, at_start=False)
    # no boundary inside the reach: no tip, the same answer `_is_tip_end` gives
    bar = Polygon([(0, 0), (20, 0), (20, 4), (0, 4)])
    assert not s6._tip_lands_on_corner([(2.0, 2.0), (5.0, 2.0)], bar, 1.0, at_start=False)
