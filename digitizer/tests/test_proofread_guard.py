"""`cfg.proofread_guard_clipped`: a shape stage 5's clip cut away, whose own
ink the art shows, is re-planned with its artwork sewn over the earlier
colour, and the re-plan is kept only when the proof-read says it is better.

Synthetic: a dark field sewn first, a red square inside it that the clip
dropped (`SHAPE_NOT_STITCHED`), the qr_code finder-square case. `replan`
stands in for `_plan_stitches` under `stage5_overlap.keep_art_scope`: it sews
the red square only when the guard names it."""
from __future__ import annotations

from types import SimpleNamespace

import numpy as np
from shapely.geometry import box

from digitizer_core import proofread_guard as pg
from digitizer_core.config import PipelineConfig
from digitizer_core.regions import Region
from digitizer_core.stitches import StitchBlock, StitchPlan
from digitizer_core.threads import chart_for
from tests.test_proofread import FABRIC, _art, _fill_runs

FIELD = box(-12, -12, 12, 12)
SQ = box(-4, -4, 4, 4)
DOT = box(16, -3, 22, 3)            # a red element outside the field, always sewn


def _nearest(cfg, rgb):
    ch = chart_for(cfg)
    best = min(range(len(ch)), key=lambda i: sum((a - b) ** 2 for a, b in zip(ch[i].rgb, rgb)))
    return best, tuple(int(v) for v in ch[best].rgb)


def _job(square_art=True):
    cfg = PipelineConfig(garment_rgb=FABRIC, garment_id="left_chest", proofread_guard_clipped=True)
    ti_red, red = _nearest(cfg, (200, 30, 30))
    ti_dark, dark = _nearest(cfg, (30, 60, 140))
    art = [(FIELD, dark), (DOT, red)] + ([(SQ, red)] if square_art else [])
    p = _art(art)
    field = Region("SF", FIELD, ti_dark, "D", FIELD.area, meta={})
    sq = Region("SQ", SQ, ti_red, "R", SQ.area, meta={})
    dot = Region("SD", DOT, ti_red, "R", DOT.area, meta={})
    result = SimpleNamespace(regions=[field, sq, dot], warnings=[],
                             proof_art=SimpleNamespace(rgb=p.rgb, bg_mask=p.bg_mask, art_bbox=p.art_bbox,
                                                       px_per_mm=p.px_per_mm))

    def replan(ids=()):
        blocks = [StitchBlock(ti_dark, "D", dark, _fill_runs(FIELD.buffer(0.3, join_style=2), "SF"))]
        warnings = []
        red_runs = _fill_runs(DOT.buffer(0.3, join_style=2), "SD")
        if "SQ" in ids:
            red_runs += _fill_runs(SQ.buffer(0.3, join_style=2), "SQ")
        blocks.append(StitchBlock(ti_red, "R", red, red_runs))
        if "SQ" not in ids:
            warnings.append({"code": "SHAPE_NOT_STITCHED", "message": "", "ids": ["SQ"]})
        return StitchPlan(blocks=blocks, palette=[{} for _ in blocks], warnings=warnings)
    return result, cfg, replan


def test_flag_is_off_by_default():
    assert PipelineConfig().proofread_guard_clipped is False


def test_a_clipped_shape_whose_ink_the_art_shows_is_sewn_and_kept():
    result, cfg, replan = _job()
    plan = pg.guard_clipped(result, cfg, replan(), replan)
    rec = plan.proofread_guard
    assert rec["accepted"] and rec["shapes"] == ["SQ"], rec
    assert rec["worse_mm2_after"] < rec["worse_mm2_before"] - pg.GUARD_MIN_MM2
    assert {r.shape_id for _b, r in plan.iter_runs()} == {"SF", "SD", "SQ"}


def test_a_clipped_shape_the_art_does_not_show_is_left_alone():
    """The art paints the field's colour where the square was traced: the
    clip was right, and the guard does not trigger."""
    result, cfg, replan = _job(square_art=False)
    first = replan()
    plan = pg.guard_clipped(result, cfg, first, replan)
    assert plan is first and plan.proofread_guard["candidates"] == 0


def test_a_replan_that_is_not_better_is_not_kept():
    result, cfg, replan = _job()
    first = replan()
    plan = pg.guard_clipped(result, cfg, first, lambda ids: first)
    rec = plan.proofread_guard
    assert plan is first and not rec["accepted"] and rec["candidates"] == 1


def test_keep_art_scope_is_empty_outside_a_guarded_replan():
    from digitizer_core import stage5_overlap as s5
    assert s5._KEEP_ART.get() == frozenset()
    with s5.keep_art_scope(["A"]):
        assert s5._KEEP_ART.get() == frozenset({"A"})
    assert s5._KEEP_ART.get() == frozenset()
    with s5.keep_art_scope([]):
        assert s5._KEEP_ART.get() == frozenset()


def test_on_a_flat_golden_the_guard_reads_and_changes_nothing():
    """The real path: `finish_generation` hands the traced raster on, the
    guard reads the plan, nothing was clipped away, so the plan is the
    golden's own (md5 as `test_small_print.py` pins it), and preflight
    carries the guard's record only with the flag on."""
    import hashlib
    import json
    from pathlib import Path
    from digitizer_core import preflight as pf
    from digitizer_core.pipeline import digitize
    from tests.conftest import FLAT_GOLDEN_MD5
    testdata = Path(__file__).resolve().parents[1] / "testdata"
    fixture = sorted(FLAT_GOLDEN_MD5)[0]
    kw = dict(target_width_mm=80.0, edge_cap="none", sew_enclosed_white=False)
    result, plan = digitize(testdata / fixture, PipelineConfig(proofread_guard_clipped=True, **kw))
    assert result.proof_art is not None
    coords = [[round(x, 4), round(y, 4), r.kind, r.jump, r.trim] for _, r in plan.iter_runs() for x, y in r.points]
    assert hashlib.md5(json.dumps(coords).encode()).hexdigest() == FLAT_GOLDEN_MD5[fixture]
    assert not plan.proofread_guard["accepted"]
    on = pf.run_preflight(result, plan, PipelineConfig(proofread_guard_clipped=True, **kw),
                          image=testdata / fixture)
    assert on["metrics"]["proofread_guard"]["rule"] == "clipped_stage5"
    off = pf.run_preflight(result, plan, PipelineConfig(**kw), image=testdata / fixture)
    assert "proofread_guard" not in off["metrics"]
    assert np.isfinite(on["metrics"]["proofread_guard"]["read_s"])
