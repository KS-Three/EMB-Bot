"""Fremont's `0020 Black` thread block, traced -- and
`cfg.extra["thread_match_skip_enlarged_text"]` (built OFF 2026-11-07).

The block had survived the excess yardstick (`thread_match_excess_gradient`)
with its cause open: Black at dE00 100 on art the grader reads as pure
white, `0015 White` loaded. `tools/thread_match_fremont_probe.py` traces each
offender through the stages that coloured it. Every stage up to the thread
match agrees the letter is black. The mislabel arrives later:
`small_text.enlarge_small_text` (reset, grow-away) scales the word THE
x1.524 and moves it into the room around it, so only 12-29% of each sewn
letter still lies on its traced ink. The grader then scores the sewn
polygon against the artwork under it, which is the white ground. The thread
is right and the grader is wrong.

Pinned on `photo/logo_hotel_fremont.webp`, 80 mm left_chest (one digitize,
shared):

* default: the block is there, and every offender is an enlarged letter
  whose traced pixels are within DELTA_E_VISIBLE of Black;
* the flag leaves every enlarged letter out of the thread grade. The block goes,
  nothing else is added, and the count lands in metrics;
* default reports carry no new metric key, and the key has one reader.

"Default" here is the grader before `thread_match_grade_traced_letter` (ON
since 2026-11-07, Kent's flip, which re-aims the grade and clears this
block): `tools.thread_match_fremont_probe.trace` pins that flag False.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest

from digitizer_core import PipelineConfig
from digitizer_core.preflight import (DELTA_E_CLEARLY_DIFFERENT, DELTA_E_VISIBLE,
                                      _enlarged_text_ids)

FLAG = "thread_match_skip_enlarged_text"


@pytest.fixture(scope="module")
def fremont():
    from tools.thread_match_fremont_probe import trace
    return trace("photo/logo_hotel_fremont.webp", "left_chest")


def test_flag_defaults_off():
    assert FLAG not in (PipelineConfig().extra or {})
    regions = [type("R", (), {"shape_id": "S1", "meta": {"small_text_enlarged": 1.5}})()]
    result = type("Res", (), {"regions": regions})()
    assert _enlarged_text_ids(result, PipelineConfig()) == set()
    on = dataclasses.replace(PipelineConfig(), extra={FLAG: True})
    assert _enlarged_text_ids(result, on) == {"S1"}


def test_the_key_has_one_reader_and_it_is_preflight():
    core = Path(__file__).resolve().parents[1] / "digitizer_core"
    readers = sorted(p.name for p in core.glob("*.py") if FLAG in p.read_text(encoding="utf-8"))
    assert readers == ["preflight.py"]


def test_default_blocks_black_on_enlarged_letters_the_palette_got_right(fremont):
    assert fremont["off"]["thread_findings"] == ["0020:block"]
    rows = fremont["rows"]
    assert len(rows) == 3
    for r in rows:
        # 1-3: the traced letter is black, and Black is its spool
        assert r["1_quantize_art_before_enlarge"]["nearest_loaded"] == "0020"
        assert r["2_palette"]["thread"] == "0020"
        assert r["3_thread_match_de"] <= DELTA_E_VISIBLE
        # 4: the enlargement moved most of the sewn letter off its ink
        e = r["4_enlarge"]
        assert e["enlarged"] and e["reset"]
        assert e["sewn_share_on_traced_letter"] < 0.5
        assert e["area_sewn_mm2"] > 2 * e["area_before_mm2"]
        # 5: the grader reads the ground that the letter grew over
        g = r["5_block_grader"]
        assert g["de_to_thread"] > DELTA_E_CLEARLY_DIFFERENT
        assert g["nearest_loaded"] == "0015"
        assert g["white_share"] > 0.5
        assert r["verdict"].startswith("grader reads the ground")


def test_default_report_carries_no_new_metric(fremont):
    assert fremont["off"]["has_skip_metric"] is False


def test_flag_drops_the_block_and_counts_what_it_skipped(fremont):
    assert fremont["on"]["thread_findings"] == []
    assert fremont["on"]["skipped"] == fremont["enlarged_regions"] > 0
    assert fremont["on"]["score"] > fremont["off"]["score"]
