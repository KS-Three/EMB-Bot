"""The A's apex is a HOLE, not an artefact of the instrument that found it.

Kent's pick 2026-09-30, after two instruments disagreed about MASTER_SCOPE
defect 49. `tools/bare_anatomy.py` reported a 3.61 mm2 gap at the apex of
ENTHUSIAST's **A**; `tools/dropped_elements.py`'s `unsewn_frac` read 0.0000 on
that fixture in every arm. A defect nobody can measure twice is a defect
nobody should build against, and the previous build was priced on the wrong
one of these two.

**Both were partly wrong, and the hole is real.** `bare_anatomy` counts satin
crosses and nothing else, so underlay threading the gap is invisible to it and
it over-reports by 1.7x here. `unsewn_frac` cannot fire on this fixture at all
— its on-ink vote is `A_ink[region].mean() > 0.5` and the largest per-region
ink fraction is 0.33, which its own docstring states. What is left when both
corrections land is about 2 mm2 of cloth, a millimetre across, at the peak of
a capital letter, and it survives the 0.50 mm opening that exists to throw
away boundary hairlines.

The reading that IS sensitive here is `uncovered_ink`: a raster mask
difference with no CIEDE2000, no opening and no colour. It shares no code with
`bare_anatomy` and puts its largest component in the whole design within a
third of a millimetre of the apex — which is what makes this two instruments
agreeing rather than one instrument repeated.

Pictures and the full trail: `docs/renders/apex-verdict-2026-09-30/`.

**That build shipped: `satin_crown_cover`, ON by default since Kent's flip
2026-10-02, folded into the code 2026-11-19.** The instrument tests that held
the PRE-FLIP engine (`satin_crown_cover=False`) and pinned how two instruments
read the hole -- `bare_anatomy` over-reporting 1.7x, the 1.93 mm2 residual
surviving the 0.50 mm opening, `uncovered_ink` agreeing on where -- went with
the flag: the hole they measured is closed on the only engine left. The record
is in this docstring and `docs/renders/apex-verdict-2026-09-30/`; what stays
is the test that the engine leaves no apex.
"""
from __future__ import annotations

from digitizer_core import PipelineConfig
from digitizer_core.pipeline import (build_generation, finish_generation,
                                     plan_stitches)
from tests.conftest import TESTDATA

FIXTURE = TESTDATA / "photo" / "enthusiast_logo.png"
WIDTH_MM, GARMENT = 80.0, "left_chest"


def _sewn(**kw):
    # On the skeleton tier, explicitly: the apex defect this file measures is
    # the skeleton tier's; the Column lane (`lettering_columns`, ON by default
    # since Kent's 2026-10-12 flip) builds the A from its outline and reads
    # 0.53 mm2 here against the 1.5 floor. Its own apex is pinned in
    # `tests/test_lettering_columns.py` and #844's A table.
    kw.setdefault("lettering_columns", False)
    cfg = PipelineConfig(target_width_mm=WIDTH_MM, garment_id=GARMENT,
                         max_colors=6, **kw)
    gen = build_generation(str(FIXTURE), cfg)
    result = finish_generation(gen.fork(), cfg)
    plan = plan_stitches(result, cfg)
    return result, plan, {r.shape_id: r.polygon for r in result.regions}


def test_the_shipped_engine_closes_the_apex():
    """Defect 49, closed: the largest thread-free component in the design is
    under the 1.5 mm2 floor the pre-flip engine held at the apex."""
    from tools.bare_anatomy import components

    _r1, plan_on, polys_on = _sewn()
    after = max(components(polys_on, plan_on, all_thread=True))[0]
    assert after < 1.5, after
