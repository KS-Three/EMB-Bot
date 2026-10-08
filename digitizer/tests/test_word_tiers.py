"""L3 mechanism: one tier per word (`cfg.lettering_word_tiers`).

The decision (`words.word_tier`) and its stamp (`assign_word_tiers`) are
pinned on synthetic words; the stage-7 reads and the stitch-width floor on
the single regions they consult. The cloth values -- the column floor and
the bean line -- are the existing flags' (ROADMAP gate 1); nothing here
asserts a value for them, only that the mechanism uses whatever is set.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from shapely.geometry import box

from digitizer_core import PipelineConfig, machine
from digitizer_core.pipeline import build_generation
from digitizer_core.regions import Region
from digitizer_core.stage7_sequence import _sews_satin, _word_tier
from digitizer_core.stitchwidth import _wanted_art_width
from digitizer_core.words import WORD_TIER_KEY, assign_word_tiers, word_groups, word_tier

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"


def _region(sid: str, poly, meta=None) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=poly.area, meta=dict(meta or {}))


def test_the_decision():
    cross = machine.SATIN_MIN_CROSS_MM
    assert word_tier(None, floor_mm=None) is None
    assert word_tier(cross + 0.1, floor_mm=None) == "satin"
    assert word_tier(cross - 0.1, floor_mm=None) == "run"
    # a floor turns the whole sub-floor band into one widened tier
    assert word_tier(cross - 0.1, floor_mm=0.8) == "widened"
    assert word_tier(0.7, floor_mm=0.8) == "widened"
    assert word_tier(0.9, floor_mm=0.8) == "satin"


def test_every_member_of_a_word_takes_the_words_tier():
    regions = [_region(f"w{i}", box(4 * i, 0, 4 * i + 3, 4)) for i in range(4)]
    for i, r in enumerate(regions):
        r.meta.update({"word_id": "WDa", "word_index": i,
                       "word_stroke_mm": machine.SATIN_MIN_CROSS_MM - 0.1})
    stray = _region("x", box(40, 40, 41, 41), {WORD_TIER_KEY: "satin"})
    n = assign_word_tiers(regions + [stray], floor_mm=None)
    assert n == 4
    assert {r.meta[WORD_TIER_KEY] for r in regions} == {"run"}
    assert WORD_TIER_KEY not in stray.meta          # stale key cleared
    assign_word_tiers(regions, floor_mm=1.0)
    assert {r.meta[WORD_TIER_KEY] for r in regions} == {"widened"}


def test_stage7_reads_the_word_only_under_the_flag():
    r = _region("a", box(0, 0, 0.3, 4), {WORD_TIER_KEY: "satin"})
    off, on = PipelineConfig(), PipelineConfig(lettering_word_tiers=True)
    assert _word_tier(r, off) is None and _word_tier(r, on) == "satin"
    assert _sews_satin(r, on, 5.0, "flat")
    r.meta[WORD_TIER_KEY] = "run"
    assert not _sews_satin(r, on, 5.0, "flat")
    r.meta["tier"] = "satin"                         # the review override wins
    assert _sews_satin(r, on, 5.0, "flat")


def test_a_widened_word_takes_the_floor_without_auto():
    r = _region("a", box(0, 0, 0.3, 4), {"stitch_width_measured_mm": 0.3,
                                          WORD_TIER_KEY: "widened"})
    target, source, deliberate = _wanted_art_width(r, pull_mm=0.2, floor_sewn_mm=1.0, auto=False)
    assert source == "floor" and deliberate and target > 0.3
    del r.meta[WORD_TIER_KEY]
    assert _wanted_art_width(r, pull_mm=0.2, floor_sewn_mm=1.0, auto=False)[1] == "shape"


@pytest.fixture(scope="module")
def becker_on():
    cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6,
                         lettering_words=True, lettering_word_tiers=True)
    return build_generation(str(TESTDATA / "becker_marine_logo.png"), cfg).regions


def test_off_writes_no_tier_and_on_stamps_every_word(becker_on):
    cfg = PipelineConfig(target_width_mm=100.0, garment_id="left_chest", max_colors=6,
                         lettering_words=True)
    off = build_generation(str(TESTDATA / "becker_marine_logo.png"), cfg).regions
    assert not any(WORD_TIER_KEY in r.meta for r in off)
    groups = word_groups(becker_on)
    assert groups and all({r.meta[WORD_TIER_KEY] for r in g} == {"satin"} for g in groups)


def test_without_words_the_tier_flag_changes_nothing():
    """No `word_id` on any region (lettering_words off): nothing to stamp."""
    regions = [_region(f"w{i}", box(4 * i, 0, 4 * i + 3, 4)) for i in range(4)]
    assert assign_word_tiers(regions, floor_mm=None) == 0
    assert not any(WORD_TIER_KEY in r.meta for r in regions)
