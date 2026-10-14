"""Hotel Fremont's small lettering at 81 mm: what `small_print_floor` gives.

`tools/fremont_small_lettering.py` replays Kent's 81 mm Hat request
(`tools/fremont_triage.py`) under nine flag arms and reads each glyph of the
THE, EAT | STAY | PLAY and EST boxes: tier, Column lane, counters, widths,
pull, stitches, trims. `docs/renders/claude-fremont-small-lettering-tier/
signatures.json` is the committed record of the tiers and counter statuses.

Three kinds of test, none skipped:

- the arm table is what the PR says it is (cheap);
- the committed record carries the findings the PR states, so a re-run that
  moves one has to say so (cheap);
- two arms are re-run LIVE and must reproduce their committed record, so the
  record is a measurement and not a story.

Measurement only: Fremont is an UNREPRESENTATIVE fixture. Pull and floor
values are cloth constants (ROADMAP gate 1); this measures them.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from tools import fremont_small_lettering as fsl
from tools import fremont_triage as ft

RECORD = (Path(__file__).resolve().parents[2] / "docs" / "renders"
          / "claude-fremont-small-lettering-tier" / "signatures.json")


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text(encoding="utf-8"))


# --- the arm table -----------------------------------------------------------

def test_arm_table_is_the_four_arms_kent_named():
    assert fsl.KENT_ARMS == ["main_81", "floor_81", "floor_stem_81", "floor_stem_92"]
    assert fsl.ARMS["main_81"][:2] == (81.0, {})
    assert fsl.ARMS["floor_81"][:2] == (81.0, {"small_print_floor": True})
    both = {"small_print_floor": True, "lettering_columns_small_stem": True}
    assert fsl.ARMS["floor_stem_81"][:2] == (81.0, both)
    assert fsl.ARMS["floor_stem_92"][:2] == (92.5, both)


def test_every_arm_flag_exists_and_is_built_off():
    """No arm flips a default: every flag an arm turns ON is OFF in the
    config today (a flipped default would make the arm a no-op), and every
    key is a real PipelineConfig field."""
    from digitizer_core import PipelineConfig
    base = PipelineConfig()
    for name, (_w, overrides, _label) in fsl.ARMS.items():
        for k, v in overrides.items():
            assert hasattr(base, k), f"{name}: {k} is not a PipelineConfig field"
            assert getattr(base, k) in (False, None), f"{name}: {k} is already ON"
            assert v not in (False, None)


def test_arms_run_the_studio_request_at_their_width():
    assert ft.studio_request(fsl.ARMS["floor_stem_92"][0])["target_width_mm"] == 92.5
    assert fsl.PRO_WIDTH_MM == 92.5


# --- the committed record carries the findings ------------------------------

def _tiers(record, arm, box):
    return record[arm]["boxes"][box]["tiers"].split()


def test_record_has_every_arm_and_the_three_boxes(record):
    assert list(record) == fsl.ARM_ORDER
    for arm in record.values():
        assert {b: v["n"] for b, v in arm["boxes"].items()} == {"the": 3, "tagline": 13, "est": 3}


def test_main_at_81_is_the_triage_reading(record):
    """#898's finding, per glyph: THE is mixed tiers (T run, H and E Column
    lane satin), the whole tagline and EST are runs."""
    assert _tiers(record, "main_81", "the") == ["R", "S*", "S*"]
    assert _tiers(record, "main_81", "tagline") == ["R"] * 13
    assert _tiers(record, "main_81", "est") == ["R"] * 3


def test_small_print_floor_moves_no_tier_at_81_or_92(record):
    """The floor is a COUNTER flag. It changes no glyph's tier in any box,
    at 81 mm or at the pro's 92.5, and neither does the small-stem rule."""
    for box in fsl.BOXES:
        assert _tiers(record, "floor_81", box) == _tiers(record, "main_81", box)
        assert _tiers(record, "floor_stem_81", box) == _tiers(record, "main_81", box)
        assert _tiers(record, "stem_81", box) == _tiers(record, "main_81", box)
        assert _tiers(record, "floor_stem_92", box) == _tiers(record, "main_92", box)


def test_floor_shuts_the_tagline_counters_at_81(record):
    """The four tagline counters (the three A's and the P): bare today only
    because the outline run leaves the middle of a blob bare, and SHUT once
    the floor plans them, at 81 mm. At 92.5 mm the A's stay open."""
    c81 = record["main_81"]["boxes"]["tagline"]["counters"]
    assert c81 == ["bare-unplanned", "bare-unplanned", "SHUT", "bare-unplanned"]
    assert record["floor_81"]["boxes"]["tagline"]["counters"] == ["SHUT"] * 4
    assert record["floor_stem_81"]["boxes"]["tagline"]["counters"] == ["SHUT"] * 4
    c92 = record["floor_stem_92"]["boxes"]["tagline"]["counters"]
    assert c92[0] == c92[1] == c92[3] == "open"


def test_small_glyph_keep_moves_no_tier_and_shuts_the_81_counters(record):
    """`small_glyph_keep` (936224e4, landed beside this) keeps the holes of
    rescued small shapes. On this tagline it plans the counters and the
    outline run around them closes them: no tier moves, 0 of 4 open."""
    for arm in ("keep_81", "keep_floor_81"):
        for box in fsl.BOXES:
            assert _tiers(record, arm, box) == _tiers(record, "main_81", box)
        assert record[arm]["boxes"]["tagline"]["counters"] == ["SHUT"] * 4


def test_size_alone_lifts_the_word_not_the_tagline(record):
    """At 92.5 mm THE is three Column-lane satin letters (the T clears
    2.25 mm^2), the tagline and EST are still all runs."""
    assert _tiers(record, "main_92", "the") == ["S*", "S*", "S*"]
    assert _tiers(record, "main_92", "tagline") == ["R"] * 13
    assert _tiers(record, "main_92", "est") == ["R"] * 3


def test_word_tiers_make_the_word_one_tier(record):
    """The flags that DO move THE: one tier per word (all run outlines)."""
    for arm in ("wordtier_81", "wordtier_floor_81", "bean_81"):
        assert _tiers(record, arm, "the") == ["R", "R", "R"]
        assert _tiers(record, arm, "tagline") == ["R"] * 13


# --- two arms re-run live ----------------------------------------------------

def _live(name):
    width, overrides, _label = fsl.ARMS[name]
    run = ft.run_arm(name, width, None, preflight=False, overrides=overrides)
    return fsl.signature(fsl.analyze_arm(name, run))


@pytest.fixture(scope="module")
def live_main():
    return _live("main_81")


@pytest.fixture(scope="module")
def live_floor_stem():
    return _live("floor_stem_81")


def _same(live, committed):
    assert live["width_mm"] == committed["width_mm"]
    assert abs(live["stitches"] - committed["stitches"]) / committed["stitches"] < 0.03
    for box, want in committed["boxes"].items():
        got = live["boxes"][box]
        assert got["tiers"] == want["tiers"], box
        assert got["counters"] == want["counters"], box
        assert got["n"] == want["n"], box


def test_live_main_reproduces_its_record(live_main, record):
    _same(live_main, record["main_81"])


def test_live_floor_and_stem_reproduces_its_record(live_floor_stem, live_main, record):
    _same(live_floor_stem, record["floor_stem_81"])
    # and moves no tier against main: the finding, live
    for box in fsl.BOXES:
        assert live_floor_stem["boxes"][box]["tiers"] == live_main["boxes"][box]["tiers"]
