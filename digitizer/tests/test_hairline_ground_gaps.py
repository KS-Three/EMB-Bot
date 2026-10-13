"""Does `cfg.hairline_over_ground` close the ground gaps the coverage guard
leaves on logos? (2026-10-13; measured, docs/renders/claude-hairline-ground-gaps/)

Measured answer, 10 logos at 80 mm / left_chest / 40 wt: NO, because it never
acts on them. On every logo with a residual, over_ground's `on_cov` and
`on_cov_gnd` arms are identical to the stitch (bare, stitches, trims):

- golden_tee: every ground is classed SATIN by stage 5's `_comp_axis` (the
  gradient lane's long cells), and a satin ground keeps only its underlap
  tongue under a strand -- `_hairline_ground` hands out nothing;
- enthusiast, gaulke: the kept strands are layer 0 -- nothing sews before them,
  and a ground sewn after a strand is left as it is today;
- what the instrument calls a "ground gap" there (gaulke 3.81 mm2) is the
  `rim`: bare cells within a cell of the strand's traced edge with NO stitched
  polygon under them -- ink beyond the trace, not a hole in a colour beneath.

These tests pin the three mechanisms on small shapes, so a change to the
satin-ground rule or the layer rule moves them on purpose. Every number is a
property of the FILE, not of cloth (ROADMAP gate 1).
"""
from __future__ import annotations

import numpy as np
from shapely.geometry import LineString, box

from digitizer_core import PipelineConfig
from digitizer_core import stage5_overlap as s5
from digitizer_core.stage5_overlap import _comp_axis, satin_ceiling_mm
from digitizer_core.stage6_hairline import hairline_candidates
from tests.test_hairline_ground import DARK, LIGHT, _region, _skin_with_strand
from tools import hairline_coverage as hc


def _ground(regions, cfg=None):
    cfg = cfg or PipelineConfig(hairline=True, hairline_over_ground=True)
    cands = hairline_candidates(regions, cfg)
    assert cands, "the strand must be a hairline candidate for the question to arise"
    return s5._hairline_ground(regions, cands, cfg, "flat", tongue_mm=0.1)


def test_a_fill_ground_sewn_before_the_strand_is_closed_under_it():
    """The control: the geometry over_ground was built for."""
    regions, _hair = _skin_with_strand()
    got = _ground(regions)
    assert got and sum(g.area for g in got.values()) > 0.5


def test_a_satin_ground_is_handed_nothing_under_the_strand():
    """golden_tee's mechanism. Two long 3 mm skin bands (stage 5 classes both
    satin) with a 0.45 mm strand slot between them: the ground keeps its
    underlap tongue, `_hairline_ground` closes nothing."""
    cfg = PipelineConfig(hairline=True, hairline_over_ground=True)
    strand = LineString([(0, -2.5), (0, 2.5)]).buffer(0.225, cap_style=2)
    band = box(-20, -1.5, 20, 1.5)
    left = band.intersection(box(-20, -2, -0.225, 2))
    right = band.intersection(box(0.225, -2, 20, 2))
    regions = [_region("Sleft", left, LIGHT, 0), _region("Sright", right, LIGHT, 0),
               _region("Sstrand", strand, DARK, 1)]
    smax = satin_ceiling_mm(cfg)
    assert all(_comp_axis(r, cfg, smax, "flat")[1] for r in regions[:2])   # satin
    assert _ground(regions, cfg) == {}


def test_a_ground_on_the_strands_own_layer_is_not_closed():
    """enthusiast / gaulke's mechanism: a strand at layer 0 has nothing sewn
    before it, so the closing has no ground to read. Same geometry as the
    control above, one layer flatter."""
    regions, _hair = _skin_with_strand()
    flat = [_region(r.shape_id, r.polygon, r.thread_index, 0) for r in regions]
    assert _ground(flat) == {}


def test_the_arms_the_tool_runs():
    kw, drop = hc.arm_setup("on_cov_gnd")
    assert kw == {"hairline": True, "hairline_coverage_guard": True, "hairline_over_ground": True}
    assert drop is True
    assert hc.arm_setup("on_gnd")[0] == {"hairline": True, "hairline_over_ground": True}
    assert "hairline_over_ground" not in hc.arm_setup("on_cov")[0]
    assert hc.arm_setup("off")[0] == {}


def _grid(cells, shape=(40, 40), cell=0.25):
    g = np.zeros(shape, bool)
    for iy, ix in cells:
        g[iy, ix] = True
    return g, (0.0, 0.0), cell


def test_the_ground_gap_splits_into_rim_and_a_hole_in_the_colour_beneath():
    """Two new bare cells just outside a strand's polygon: one with a stitched
    shape under it (a hole in the colour beneath: `ground`), one with none
    (ink beyond the traced edge: `rim`). `ground_mm2` keeps both."""
    strand = box(2.0, 2.0, 6.0, 2.5)                 # a 4 x 0.5 mm strand
    beneath = box(2.0, 2.5, 6.0, 4.0)                # the colour it sits on, above
    off = _grid([])
    on = _grid([(7, 12),                             # y 1.75-2.0: below the strand, nothing there
                (10, 12)])                           # y 2.5-2.75: inside `beneath`
    att = hc.attribute(off, on, {"S": strand}, plan=_NoRuns(),
                       stitched=strand.union(beneath))
    s = att["per_shape"]["S"]
    assert s["ground_mm2"] == 0.12                   # 2 cells x 0.0625, rounded
    assert s["rim_mm2"] == 0.06
    assert s["new_bare_mm2"] == 0.12


class _NoRuns:
    def iter_runs(self):
        return iter(())
