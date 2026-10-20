"""The counter census (`tools/counter_census.py`, 2026-10-15): the quantity the
true-size switch's counter-width guard will read. Measure-only tool; these pin
its two readings and its table, not any engine behaviour."""
from __future__ import annotations

import json
import sys
from pathlib import Path

from shapely.geometry import Point, Polygon, box

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core.regions import Region  # noqa: E402
from tools import counter_census as cc  # noqa: E402


def test_inscribed_width_of_a_round_and_a_slot_counter():
    assert abs(cc.inscribed_width_mm(Point(0, 0).buffer(0.25, 64).exterior) - 0.5) < 0.05
    # a 0.4 x 3 mm slot is 0.4 across, however long
    assert abs(cc.inscribed_width_mm(box(0, 0, 3, 0.4).exterior) - 0.4) < 0.05


def _letter(sid, x, hole_r=None, h=2.0, thread=7):
    outer = box(x, 0, x + 1.4, h)
    poly = outer if hole_r is None else Polygon(outer.exterior, [Point(x + 0.7, h / 2).buffer(hole_r, 32).exterior.coords[::-1]])
    return Region(sid, poly, thread, str(thread), float(poly.area), meta={"text_cluster_id": "TC1"})


def test_a_line_reads_its_smallest_counter_and_a_line_with_none_reads_none():
    line = [_letter("Sa", 0, 0.30), _letter("Sb", 2, 0.22), _letter("Sc", 4)]
    (row,) = cc.lines_of(line)
    assert row["n"] == 3 and row["counters"] == 2
    assert abs(row["min_counter_mm"] - 0.44) < 0.05
    (bare,) = cc.lines_of([_letter("Sd", 0), _letter("Se", 2), _letter("Sf", 4)])
    assert bare["min_counter_mm"] is None and bare["counters"] == 0
    assert cc.lines_of(line[:2]) == []                      # two shapes are not a line


def test_the_table_marks_hold_pass_and_no_counter(tmp_path):
    rec = {"design": "d", "lines": [
        {"cluster": "A", "n": 3, "cap_mm": 1.3, "min_counter_mm": 0.40, "counters": 2, "bean": 3, "word": None, "verdict": "LOSS"},
        {"cluster": "B", "n": 4, "cap_mm": 1.6, "min_counter_mm": 0.55, "counters": 3, "bean": 4, "word": "1895", "verdict": "WIN"},
        {"cluster": "C", "n": 3, "cap_mm": 2.6, "min_counter_mm": None, "counters": 0, "bean": 3, "word": "the", "verdict": "WIN"}]}
    (tmp_path / "census_d.json").write_text(json.dumps(rec))
    t = cc.table(tmp_path)
    assert "| d | A | 3 | 1.30 | 0.40 | 2 | 3 | - | LOSS | HOLD |" in t
    assert "| 0.55 | 3 | 4 | 1895 | WIN | pass |" in t
    assert "| - | 0 | 3 | the | WIN | pass (no counter) |" in t
