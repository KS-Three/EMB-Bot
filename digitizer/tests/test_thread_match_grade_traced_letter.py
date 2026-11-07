"""`cfg.extra["thread_match_grade_traced_letter"]` (built OFF 2026-11-07):
grade an enlarged letter's thread on the polygon it was TRACED from.

PR #1312 traced Fremont's false `0020 Black` block ("reassign to 0015
White") to the grader: `small_text.enlarge_small_text` scales the word THE
x1.524 and moves it into the room around it, and preflight then scores the
SEWN polygon against the white ground it grew over. #1312 built the skip
(`thread_match_skip_enlarged_text`, OFF); this is its option B. `small_text`
keeps each moved letter's incoming polygon in `meta[TRACED_POLYGON_KEY]`
(metadata only, unconditional: no stage reads it), and under the flag the
grader reads that polygon instead. Unlike the skip, the letter is still
graded, so a wrong spool on an enlarged letter still fires.

Pinned on `photo/logo_hotel_fremont.webp`, 80 mm left_chest (one digitize):

* every enlarged letter carries its traced polygon, and it is exactly the
  polygon that went into `enlarge_small_text` (the #1312 probe's spy);
* default: the Black block is there, no new metric key;
* the flag: the Black block goes, every enlarged letter is still graded
  (same rows as default), each now within DELTA_E_VISIBLE of its spool;
* the flag has one reader (preflight), and a re-drawn or shade-banded region
  is graded as sewn.
"""
from __future__ import annotations

import dataclasses
from pathlib import Path

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import PipelineConfig, digitize
from digitizer_core.preflight import (DELTA_E_VISIBLE, THREAD_MATCH_POOR,
                                      _GRADE_TRACED_KEY, _region_color_errors,
                                      _traced_letters, _two_tone_view,
                                      run_preflight)
from digitizer_core.small_text import TRACED_POLYGON_KEY
from digitizer_core.stage1_prep import prep

FLAG = "thread_match_grade_traced_letter"
ART = Path(__file__).resolve().parents[1] / "testdata" / "photo" / "logo_hotel_fremont.webp"


def _on(cfg: PipelineConfig) -> PipelineConfig:
    return dataclasses.replace(cfg, extra={**(cfg.extra or {}), FLAG: True})


def _blocks(rep) -> list[str]:
    return sorted(f"{f['extra']['thread_number']}:{f['severity']}"
                  for f in rep["findings"] if f["code"] == THREAD_MATCH_POOR)


@pytest.fixture(scope="module")
def fremont():
    from tools.thread_match_fremont_probe import EnlargeSpy
    cfg = PipelineConfig(target_width_mm=80.0, garment_id="left_chest")
    with EnlargeSpy() as spy:
        result, plan = digitize(ART, cfg)
    view = _two_tone_view(prep(ART, cfg, design_class=result.design_class), plan, cfg)
    return {"cfg": cfg, "result": result, "plan": plan, "spy": spy, "view": view,
            "off": run_preflight(result, plan, cfg, image=ART),
            "on": run_preflight(result, plan, _on(cfg), image=ART)}


def test_flag_defaults_off_and_has_one_reader():
    assert FLAG == _GRADE_TRACED_KEY
    assert FLAG not in (PipelineConfig().extra or {})
    core = Path(__file__).resolve().parents[1] / "digitizer_core"
    readers = sorted(p.name for p in core.glob("*.py") if FLAG in p.read_text(encoding="utf-8"))
    assert readers == ["preflight.py"]


def test_traced_letters_empty_off_and_guarded_on():
    t = box(0, 0, 1, 1)
    R = type("R", (), {})
    regs = []
    for sid, meta in (("S1", {TRACED_POLYGON_KEY: t}),
                      ("S2", {TRACED_POLYGON_KEY: t, "boundary_override": [[0, 0]]}),
                      ("S3", {TRACED_POLYGON_KEY: t, "holes_override": []}),
                      ("S4", {TRACED_POLYGON_KEY: t}),
                      ("S5", {TRACED_POLYGON_KEY: Polygon()}),
                      ("S6", {})):
        r = R()
        r.shape_id, r.meta = sid, meta
        regs.append(r)
    result = type("Res", (), {"regions": regs})()
    assert _traced_letters(result, PipelineConfig()) == {}
    # re-drawn (S2, S3), shade-banded (S4), empty (S5), never moved (S6): as sewn
    assert _traced_letters(result, _on(PipelineConfig()), {"S4": {7: []}}) == {"S1": t}


def test_every_enlarged_letter_keeps_the_polygon_it_came_in_with(fremont):
    regions = fremont["result"].regions
    enlarged = [r for r in regions if r.meta.get("small_text_enlarged")]
    assert len(enlarged) >= 3
    for r in regions:
        traced = r.meta.get(TRACED_POLYGON_KEY)
        moved = r.meta.get("small_text_enlarged") or r.meta.get("small_text_inner")
        assert (traced is not None) == bool(moved), r.shape_id
        if traced is not None:
            assert traced.equals_exact(fremont["spy"].before[id(r)], 0.0)
            assert not traced.equals(r.polygon)


def test_default_blocks_black_and_adds_no_metric(fremont):
    assert "0020:block" in _blocks(fremont["off"])
    assert "thread_match_traced_letters_graded" not in fremont["off"]["metrics"]


def test_flag_grades_the_traced_letter_and_the_block_goes(fremont):
    res, plan, view, cfg = fremont["result"], fremont["plan"], fremont["view"], fremont["cfg"]
    enlarged = {r.shape_id for r in res.regions if r.meta.get("small_text_enlarged")}
    rows_off = {r["shape_id"]: r for r in _region_color_errors(view, res, plan, cfg)
                if r["shape_id"] in enlarged}
    rows_on = {r["shape_id"]: r for r in _region_color_errors(view, res, plan, _on(cfg))
               if r["shape_id"] in enlarged}
    # No silent skip: every enlarged letter graded by default is graded under the flag.
    assert rows_off and set(rows_on) == set(rows_off)
    assert max(r["delta_e"] for r in rows_off.values()) > DELTA_E_VISIBLE
    assert all(r["delta_e"] <= DELTA_E_VISIBLE for r in rows_on.values())
    assert "0020:block" not in _blocks(fremont["on"])
    assert fremont["on"]["score"] > fremont["off"]["score"]
    assert fremont["on"]["metrics"]["thread_match_traced_letters_graded"] == len(
        _traced_letters(res, _on(cfg)))
    # Nothing but the moved letters' rows changes.
    other_off = [r for r in _region_color_errors(view, res, plan, cfg)
                 if r["shape_id"] not in _traced_letters(res, _on(cfg))]
    other_on = [r for r in _region_color_errors(view, res, plan, _on(cfg))
                if r["shape_id"] not in _traced_letters(res, _on(cfg))]
    assert [(r["shape_id"], r["delta_e"]) for r in other_off] == \
        [(r["shape_id"], r["delta_e"]) for r in other_on]
