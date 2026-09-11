"""The catalogue: one set of readers, pointed at two files.

Spec §5. Tier is read by the same scale-free rule on both sides
(`satin_columns` share, then `union_pitch` rows); `study_pro.classify` is
never pointed at ours (its 0.7 mm floor).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import box

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "tools"))
sys.path.insert(0, str(HERE.parent / "tools" / "pro_parity"))

import proloop_synth as synth                        # noqa: E402
import pairframe                                     # noqa: E402
import diff as pdiff                                 # noqa: E402
from test_pro_overlay import becker_pair             # noqa: E402,F401  (session fixture)


def _two_regions(ours_tier_b="satin", pro_tier_b="fill", width_b=2.0):
    """Region A: satin on both sides. Region B: satin ours, `pro_tier_b` pro.

    R1 (controller ruling): the fill arm uses `fill_passes(0, 8, 20, 4.0,
    row=0.4, stitch=2.5)` rather than the brief's `fill_passes(0, 9, 20,
    2.0)`, which yields ~48 segments -- under `row_pitch_union.union_pitch`'s
    50-segment floor, so `tier_of` would misread the fill arm as "run"
    instead of "fill". This arm measures 88 segments (11 rows), well clear
    of the floor. Region B's box is widened to (-0.5, 7.5, 20.5, 12.5) to
    contain both the widened fill arm (y in [8, 12]) and the unchanged
    satin arm (`satin_pass(0, 10, 20, ...)`, y in [9, 11]).
    """
    a_ours = synth.satin_pass(0, 0, 20, 2.0)
    a_pro = synth.satin_pass(0, 0, 20, 2.0)
    b_ours = ([synth.satin_pass(0, 10, 20, 2.0)] if ours_tier_b == "satin"
              else synth.fill_passes(0, 8, 20, 4.0, row=0.4, stitch=2.5))
    b_pro = ([synth.satin_pass(0, 10, 20, width_b)] if pro_tier_b == "satin"
             else synth.fill_passes(0, 8, 20, 4.0, row=0.4, stitch=2.5))
    ours = [((0, 0, 0), [a_ours, *b_ours])]
    pro = [((0, 0, 0), [a_pro, *b_pro])]
    regions = [("A", "satin", box(-0.5, -1.5, 20.5, 1.5)), ("B", "satin", box(-0.5, 7.5, 20.5, 12.5))]
    return pro, ours, regions


def test_tier_disagreement_shows_on_one_row(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="fill")
    d = synth.make_prep_dir(tmp_path, "tier", pro, ours, regions, [(0, -1, 20, 1), (0, 8, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, residual = pdiff.region_rows(pair, reg)
    by = {r["shape_id"]: r for r in rows}
    assert by["A"]["ours"]["tier"] == "satin" and by["A"]["pro"]["tier"] == "satin"
    assert by["B"]["ours"]["tier"] == "satin" and by["B"]["pro"]["tier"] == "fill"
    assert by["B"]["tier_planned"] == "satin"
    assert residual["pro_passes"] == 0 and residual["ours_passes"] == 0


def test_width_difference_is_a_width_row_not_a_tier_row(tmp_path):
    pro, ours, regions = _two_regions(pro_tier_b="satin", width_b=2.6)
    d = synth.make_prep_dir(tmp_path, "width", pro, ours, regions, [(0, -1, 20, 1), (0, 8, 20, 12)], 20.0)
    pair = pairframe.load_pair(d)
    reg = pairframe.register_pair(pair.pro_path, pair.ours_path)
    rows, _ = pdiff.region_rows(pair, reg)
    b = next(r for r in rows if r["shape_id"] == "B")
    assert b["ours"]["tier"] == b["pro"]["tier"] == "satin"
    assert abs(b["ours"]["width_p50"] - 2.0) < 0.15 and abs(b["pro"]["width_p50"] - 2.6) < 0.15


def test_readers_agree_between_plan_and_file(becker_pair):
    """`passes_from_file` on ours.dst measures what `passes_from_plan` would:
    the DST round trip does not move a column width (spec §7 test 6)."""
    from satin_columns import measure, passes_from_file
    from digitizer_core import PipelineConfig, digitize
    import prep_all
    cfg = prep_all.parity_config(becker_pair.width_mm, "left_chest")
    _res, plan = digitize(becker_pair.art, cfg)
    from satin_columns import passes_from_plan
    a = measure(passes_from_plan(plan))
    b = measure(passes_from_file(becker_pair.ours_path))
    assert abs(a["median_mm"] - b["median_mm"]) < 0.05
    assert abs(a["share"] - b["share"]) < 0.02
