"""`cfg.satin_thin_arm_stop` -- a thin arm stops at a much wider node.

Built OFF 2026-11-17 (prime grader, Toat Machine's M). The script M's
hairline joins each thick stem near its top. Two junction rules treat that
arm like any other: `satin_junction_stack` runs it INTO the node by its own
half-width, and `_is_tip_end` caps it (`_extend_to_cap`), so a fan of crosses
lands across the stem's own crosses. ON, an arm whose node is at least
`_THIN_ARM_RATIO` times its own width stops at the blob's edge with neither.
"""
from __future__ import annotations

import numpy as np

from digitizer_core import PipelineConfig
from digitizer_core import stage6_satin as s6
from tests.conftest import own_thread_only


class _Field:
    """half_at = 0.8 along the arm (y < 6), 2.4 at the node (y >= 6)."""

    def half_at(self, pt):
        return 0.8 if pt[1] < 6.0 else 2.4


def test_the_flag_is_off_by_default():
    assert PipelineConfig().satin_thin_arm_stop is False
    assert PipelineConfig(satin_thin_arm_stop=True).satin_thin_arm_stop is True


def test_a_thin_arm_into_a_wide_node_is_read():
    spine = [(0.0, float(y)) for y in np.arange(0.0, 6.5, 0.5)] + [(0.0, 7.0)]
    assert s6._meets_wider(spine, _Field(), at_start=False)
    assert s6._meets_wider(list(reversed(spine)), _Field(), at_start=True)


def test_an_arm_as_wide_as_its_node_is_not():
    class Even:
        def half_at(self, pt):
            return 1.0

    spine = [(0.0, float(y)) for y in np.arange(0.0, 7.0, 0.5)]
    assert not s6._meets_wider(spine, Even(), at_start=False)


def test_a_spine_too_short_to_read_is_not():
    assert not s6._meets_wider([(0.0, 0.0), (0.0, 1.0)], _Field(), at_start=False)


def test_the_flag_reaches_the_emitter():
    """Toat Machine at 89.5 mm on a hat: ON, the reading is asked and the
    plan changes; OFF it is never asked. A dropped `thin_arm_stop=` anywhere
    on the path would turn ON into OFF with the units above still green."""
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from tests.conftest import TESTDATA

    calls = []
    orig = s6._meets_wider

    def spy(*a, **k):
        calls.append(1)
        return orig(*a, **k)

    gen = None
    counts = {}
    for on in (False, True):
        cfg = PipelineConfig(target_width_mm=89.5, garment_id="hat_front", max_colors=6,
                             satin_thin_arm_stop=on)
        if gen is None:
            gen = build_generation(str(TESTDATA / "art" / "logo_toat_machine.png"), cfg)
        result = finish_generation(gen.fork(), cfg)
        calls.clear()
        s6._meets_wider = own_thread_only(spy, orig)
        try:
            plan = plan_stitches(result, cfg)
        finally:
            s6._meets_wider = orig
        counts[on] = (len(calls), plan.stats.stitch_count)
    assert counts[False][0] == 0
    assert counts[True][0] > 0
    assert counts[True][1] != counts[False][1]
