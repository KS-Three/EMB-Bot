"""`cfg.satin_tip_caps` — a tapered TIP is a cap, not a junction.

Built OFF 2026-09-29 for MASTER_SCOPE defect 49. Under `satin_rail_comp` a
shape keeps its artwork polygon and the artwork's sharp tips are sharp, so a
tip that one stroke ran through on the grown polygon becomes a NODE where two
arms end. Both ends read `free_end=False`, `_extend_to_cap` never runs, and
the junction trim pulls both arms back on top of the half-width the medial
axis already stopped short by.

ON, a junction end with no single owner whose artwork boundary sits within
`_TIP_REACH_HALVES` sewn half-widths along its own end tangent is capped
instead of tucked.

**What it buys, measured 2026-09-29 over the nine REAL_ART logos at their own
census widths** (`tools/bare_anatomy.py`): bare artwork falls on ALL NINE,
end gaps on all nine — becker 182.07 → 160.69 mm², golden_tee 56.38 → 46.20,
bridge 59.57 → 52.30, screenshot 32.79 → 27.67 (its worst component 1.94 →
0.91). The price is thread: +0.5% stitches (fremont) to +12.7% (golden_tee,
also the largest coverage gain), median about +3.6%, and trims −1 to +11.

**What it does NOT buy, and this is not a gap in the test.** It does not close
defect 49's own case. ENTHUSIAST's A apex stays at 3.61 mm² because BOTH its
arms have an identified `tuck_under` partner — each tucks under the other —
so the tip test is never reached on them. That is a construction call, not a
bug, and the reasoning that an area test could separate a tip from a corner
is refuted in DOCTRINE ("Beyond the node cannot tell a tapered TIP from a
CORNER"). Deliberately NOT asserted here: a build that closes the apex must
not have to edit this file to land.

OFF is byte-identical to the pre-flag engine — verified 2026-09-29 as plan
digests over all nine corpus logos across two trees, which is why the cheap
structural check below is enough to keep it that way.
"""
from __future__ import annotations

import math

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from tests.conftest import TESTDATA


def test_the_flag_is_on_by_default_since_2026_09_29():
    """Kent's flip on the corpus price (scope-history, the nine-logo table):
    bare artwork falls on all nine logos for a median +3.6% stitches. False
    stays reachable and is the pre-flip engine, byte-identical."""
    assert PipelineConfig().satin_tip_caps is True
    assert PipelineConfig(satin_tip_caps=False).satin_tip_caps is False


def test_a_tip_reads_as_a_tip_and_a_corridor_does_not():
    """`_is_tip_end` on the two shapes it has to tell apart.

    A spine ending one half-width short of a tapered cap has the boundary
    inside its reach; a spine ending in the middle of a long bar has open
    corridor ahead of it for far longer than any tip.
    """
    half_sewn = 1.0
    # a bar 4 mm wide: a spine end 1 mm short of the right cap IS a tip
    bar = Polygon([(0, 0), (10, 0), (10, 4), (0, 4)])
    assert s6._is_tip_end([(7.0, 2.0), (9.0, 2.0)], bar, half_sewn, at_start=False)
    # the same end aimed back down a 10 mm corridor is not
    assert not s6._is_tip_end([(9.0, 2.0), (5.0, 2.0)], bar, half_sewn, at_start=False)
    # and a degenerate spine never is
    assert not s6._is_tip_end([(5.0, 2.0), (5.0, 2.0)], bar, half_sewn, at_start=False)
    assert not s6._is_tip_end([(5.0, 2.0)], bar, half_sewn, at_start=False)


def test_the_reach_is_stated_in_sewn_terms():
    """The gate scales with the SEWN half-width, so it reads the same column
    off the rails and on them. A zero or negative half is never a tip —
    there is no reach to measure."""
    bar = Polygon([(0, 0), (10, 0), (10, 4), (0, 4)])
    spine = [(6.0, 2.0), (8.0, 2.0)]          # end 2 mm short of the cap
    assert not s6._is_tip_end(spine, bar, 1.0, at_start=False)   # reach 1.6
    assert s6._is_tip_end(spine, bar, 1.5, at_start=False)       # reach 2.4
    assert not s6._is_tip_end(spine, bar, 0.0, at_start=False)


def test_on_the_lettering_fixture_it_buys_end_coverage_for_thread():
    """ENTHUSIAST at 80 mm, the flip's own fixture, with the flag ON.

    Pinned as a FLOOR on what it buys and a CEILING on what it costs, the way
    the rail-comp trims are: a cheaper or more effective build keeps this
    green. Measured 2026-09-29: end bare 10.49 → 9.18 mm² for 2,392 → 2,474
    stitches at the same 15 trims.

    **Re-pinned 2026-09-30 for the widened gate** (Kent's apex construction):
    end bare 9.18 → **3.61 mm²** and stitches 2,474 → **2,602**. The end-bare
    bar tightens with the gain rather than tracking it loosely — the apex the
    first build could not reach is what closed, so the floor should not let it
    re-open.

    One digitize, not two — the OFF numbers are the constants above, and this
    suite already pays for an ENTHUSIAST run in `test_rail_comp.py`.
    """
    from tools.bare_anatomy import components

    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest",
                         max_colors=6, satin_tip_caps=True)
    gen = build_generation(str(TESTDATA / "photo" / "enthusiast_logo.png"), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    polys = {r.shape_id: r.polygon for r in result.regions}
    comps = components(polys, plan)
    assert comps

    end_bare = sum(a for a, _h, is_end, _s in comps if is_end)
    assert end_bare <= 4.0, f"end bare rose to {end_bare:.2f} mm2 (3.61 when widened)"
    # and the thread it costs stays inside the measured price (2,602 of 2,392)
    assert plan.stats.stitch_count <= 2650, plan.stats.stitch_count
    assert plan.stats.trims <= 15, plan.stats.trims
