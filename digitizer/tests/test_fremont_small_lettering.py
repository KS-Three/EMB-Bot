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
    off = fsl.PRE_TRUE_SIZE                     # every arm: the engine before 2026-10-14
    assert fsl.ARMS["main_81"][:2] == (81.0, off)
    assert fsl.ARMS["floor_81"][:2] == (81.0, {**off, "small_print_floor": True})
    both = {**off, "small_print_floor": True, "lettering_columns_small_stem": True}
    assert fsl.ARMS["floor_stem_81"][:2] == (81.0, both)
    assert fsl.ARMS["floor_stem_92"][:2] == (92.5, both)


def test_every_arm_flag_exists_and_is_built_off():
    """No arm is a no-op: every override moves its flag AWAY from the config
    default (an arm that sets a flag to the value it already has measures
    nothing), and every key is a real PipelineConfig field. The flags the
    arms turn ON are OFF today; `small_glyph_keep` is the one default that
    flipped ON (2026-10-13, Kent), so its arms turn it OFF."""
    from digitizer_core import PipelineConfig
    # `small_text_true_size` flipped ON 2026-10-14; every arm pins it OFF (the
    # record predates the flip), so the others are judged against that engine.
    assert PipelineConfig().small_text_true_size is True
    base = PipelineConfig(**fsl.PRE_TRUE_SIZE)
    for name, (_w, overrides, _label) in fsl.ARMS.items():
        assert overrides["small_text_true_size"] is False, name
        for k, v in overrides.items():
            assert hasattr(base, k), f"{name}: {k} is not a PipelineConfig field"
            if k in fsl.PRE_TRUE_SIZE and v == fsl.PRE_TRUE_SIZE[k]:
                continue                        # the pre-flip base, not an arm
            if k == "small_glyph_keep":
                assert base.small_glyph_keep is True, f"{name}: keep is no longer the default"
                assert v is False, f"{name}: {k} is already ON"
            else:
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
    """The four tagline counters (the three A's and the P): with
    `small_glyph_keep` OFF (`nokeep_81`, the engine before 2026-10-13) they
    were bare only because the outline run leaves the middle of a blob bare,
    and SHUT once the floor planned them. Keep ON is the default now, so
    plain main and the floor arms all shut them at 81 mm."""
    nokeep = record["nokeep_81"]["boxes"]["tagline"]["counters"]
    assert nokeep == ["bare-unplanned", "bare-unplanned", "SHUT", "bare-unplanned"]
    assert record["nokeep_floor_81"]["boxes"]["tagline"]["counters"] == ["SHUT"] * 4
    for arm in ("main_81", "floor_81", "floor_stem_81"):
        assert record[arm]["boxes"]["tagline"]["counters"] == ["SHUT"] * 4


def test_keep_on_leaves_no_tagline_counter_open_at_92(record):
    """At 92.5 mm the A's used to stay open (measured with keep OFF); with
    the keep ON, as it is by default, none is open: they are SHUT, and the
    one the floor + small-stem arm leaves unplanned is bare, not open."""
    for arm in ("main_92", "floor_stem_92"):
        assert "open" not in record[arm]["boxes"]["tagline"]["counters"]


def test_small_glyph_keep_moves_no_tier_and_shuts_the_81_counters(record):
    """`small_glyph_keep` (936224e4, ON by default since 2026-10-13) keeps
    the holes of rescued small shapes. On this tagline it plans the counters
    and the outline run around them closes them: no tier moves against the
    OFF controls, and 0 of 4 are open or bare-unplanned (OFF: 3 bare)."""
    for arm in ("nokeep_81", "nokeep_floor_81"):
        for box in fsl.BOXES:
            assert _tiers(record, arm, box) == _tiers(record, "main_81", box)
    assert record["main_81"]["boxes"]["tagline"]["counters"] == ["SHUT"] * 4


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
