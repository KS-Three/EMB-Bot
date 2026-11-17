"""`tools/prime_grader.py`'s pure helpers: no engine, no pictures."""
import json

import pytest

from tools import prime_grader as pg

ITEM = {"id": "L_x", "size": "60 x 40 mm on hat_front", "w_mm": 60.0, "h_mm": 40.0,
        "tiles": [{"name": "A1"}, {"name": "A2"}]}


def verdict(**over):
    v = {"item": "L_x", "grade": "Okay", "whole": [], "reason": "edges are rough",
         "tiles_read": ["A1", "A2"],
         "faults": [{"x_mm": 10, "y_mm": 5, "what": "jagged", "severity": "noticeable",
                     "note": "the border stair-steps", "seen_in": "A1"}]}
    v.update(over)
    return v


def test_the_rubric_is_the_pinned_one():
    # A changed rubric is a new dated version: bump RUBRIC_VERSION and the sha together.
    assert pg.rubric_sha() == pg.RUBRIC_SHA256
    assert pg.RUBRIC_VERSION in pg.RUBRIC.read_text(encoding="utf-8").splitlines()[0]


def test_the_rubric_names_every_kind_grade_and_tick():
    text = pg.RUBRIC.read_text(encoding="utf-8")
    for word in (*pg.WHATS, *pg.WHOLE, *pg.SEVERITIES, *pg.GRADES):
        assert word in text, word


def test_every_kind_has_a_class():
    assert set(pg.CLASS_OF) == set(pg.WHATS)


def test_tile_grid_covers_the_design_and_respects_the_cap():
    for w, h in ((102.0, 64.7), (20.0, 12.0), (300.0, 200.0), (114.0, 42.0)):
        tiles = pg.tile_grid(w, h)
        assert 1 <= len(tiles) <= pg.MAX_TILES
        assert min(t["x0"] for t in tiles) == 0 and min(t["y0"] for t in tiles) == 0
        assert max(t["x1"] for t in tiles) == pytest.approx(w, abs=0.02)
        assert max(t["y1"] for t in tiles) == pytest.approx(h, abs=0.02)
        assert len({t["name"] for t in tiles}) == len(tiles)
    assert pg.tile_grid(20.0, 12.0)[0]["name"] == "A1"


def test_clean_verdict_keeps_a_good_one():
    rec = pg.clean_verdict(verdict(), ITEM)
    assert rec["grade"] == "Okay" and rec["faults"][0]["what"] == "jagged"


@pytest.mark.parametrize("over, word", [
    ({"grade": "Fine"}, "grade"),
    ({"whole": ["ugly"]}, "whole"),
    ({"reason": " "}, "reason"),
    ({"tiles_read": ["A1"]}, "tiles_read"),
    ({"item": "L_y"}, "item"),
    ({"faults": [{"x_mm": 500, "y_mm": 5, "what": "jagged", "severity": "ruins", "note": "n", "seen_in": "A1"}]},
     "off the design"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "ugly", "severity": "ruins", "note": "n", "seen_in": "A1"}]}, "what"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "gap", "severity": "bad", "note": "n", "seen_in": "A1"}]}, "severity"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "gap", "severity": "ruins", "note": "", "seen_in": "A1"}]}, "note"),
    ({"faults": [{"x_mm": 5, "y_mm": 5, "what": "gap", "severity": "ruins", "note": "n", "seen_in": "Z9"}]}, "seen_in"),
])
def test_clean_verdict_refuses_what_the_rubric_does_not_allow(over, word):
    with pytest.raises(ValueError, match=word):
        pg.clean_verdict(verdict(**over), ITEM)


def _kit_and_readings():
    kit = {"items": [ITEM, {**ITEM, "id": "L_y"}]}
    readings = {"items": {
        "L_x": pg.clean_verdict(verdict(), ITEM),
        "L_y": pg.clean_verdict(verdict(item="L_y", grade="Bad", faults=[
            {"x_mm": 1, "y_mm": 1, "what": "wavy", "severity": "ruins", "note": "n", "seen_in": "A1"},
            {"x_mm": 2, "y_mm": 2, "what": "pen_flow", "severity": "nitpick", "note": "n", "seen_in": "A2"}]),
            {**ITEM, "id": "L_y"})}}
    return kit, readings


def test_rollup_counts_gross_faults_by_class_and_design():
    ru = pg.rollup(*_kit_and_readings())
    assert ru["designs"] == 2 and ru["grades"]["Okay"] == 1 and ru["grades"]["Bad"] == 1
    assert ru["mean_step"] == 2.5
    assert ru["classes"] == {"edge": ["L_x", "L_y"]}          # the nitpick pen_flow is not gross
    assert ru["rows"][1]["ruins"] == 1 and ru["rows"][1]["nitpick"] == 1


def test_movement_reports_grade_steps_and_class_changes():
    kit, readings = _kit_and_readings()
    prev = {"rollup": pg.rollup(kit, readings)}
    assert pg.movement(pg.rollup(kit, readings), prev) == []
    readings["items"]["L_y"]["grade"] = "Good"
    readings["items"]["L_y"]["faults"] = []
    (m,) = pg.movement(pg.rollup(kit, readings), prev)
    assert m == {"id": "L_y", "was": "Bad", "grade": "Good", "steps": -2, "gained": [], "cleared": ["edge"]}
    assert pg.movement(pg.rollup(kit, readings), None) == []


def test_weighted_kappa():
    assert pg.weighted_kappa([0, 1, 2, 3, 4], [0, 1, 2, 3, 4]) == 1.0
    assert pg.weighted_kappa([0, 0, 4, 4], [4, 4, 0, 0]) == -1.0
    assert pg.weighted_kappa([2, 2], [2, 2]) is None
    k = pg.weighted_kappa([0, 1, 2, 3, 4, 2], [1, 1, 2, 4, 4, 3])
    assert 0 < k < 1


def test_pin_rows_separates_a_hit_from_a_same_class_hit():
    pins = [{"x_mm": 10, "y_mm": 5, "what": "wavy", "severity": "noticeable"},
            {"x_mm": 10, "y_mm": 5, "what": "colour", "severity": "ruins"},
            {"x_mm": 50, "y_mm": 30, "what": "jagged", "severity": "ruins"}]
    faults = [{"x_mm": 11, "y_mm": 6, "what": "jagged"}]
    rows = pg.pin_rows(pins, faults)
    assert [(r["hit"], r["hit_class"]) for r in rows] == [(True, True), (True, False), (False, False)]


def test_scorecard_markdown_states_what_it_is(tmp_path):
    kit, readings = _kit_and_readings()
    card = {"date": "2026-11-17", "rubric_version": pg.RUBRIC_VERSION, "rubric_sha256": pg.RUBRIC_SHA256,
            "tree_sha": "abcdef123456", "rollup": pg.rollup(kit, readings), "yardstick": {},
            "readings": readings["items"], "prev_date": None, "movement": []}
    md = pg.scorecard_markdown(card)
    assert "not a quality claim" in md and "`L_y`" in md and "the border stair-steps" in md
    json.dumps(card)
