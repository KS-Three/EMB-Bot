"""Small print at 60 wt (`tools/small_print_census.py`, 2026-10-14): measure only.

The census drives `tools/small_print.py` over caps x {40, 60} wt x
`small_print_floor` OFF/ON; no engine file changed. These pin:

- the neighbouring flags the census holds at their shipped defaults (the
  table says which engine it was measured on);
- the narrowest-column reader on hand-built runs;
- the 60 wt OFF row on the synthetic BOARD word at a 3 mm cap, measured
  2026-10-14 (Windows): 532 stitches, 8 of 10 counters shut, 0.34 of the
  counter area open, dust 0.100, narrowest column 0.64 mm. Ranges, not a
  stream hash: the row is a measurement, the OFF path itself is md5-pinned in
  `test_small_print.py`. Every number is a candidate (ROADMAP gate 1).
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from digitizer_core import PipelineConfig, stitches  # noqa: E402
from tools import small_print, small_print_census as census  # noqa: E402

TESTDATA = Path(__file__).resolve().parents[1] / "testdata"


def test_the_neighbouring_flags_sit_at_their_shipped_defaults():
    cfg = PipelineConfig()
    assert census.PINNED == {"small_glyph_keep": True, "small_lettering_skeleton": False,
                             "small_text_cap_mm": None, "small_text_true_size": True,
                             "small_text_restore_mm": 3.0}
    for k, v in census.PINNED.items():
        assert getattr(cfg, k) == v, k
    assert cfg.small_print_floor is False and cfg.thread_wt == 40


def _satin(crosses, x0=0.0):
    pts = []
    for i, w in enumerate(crosses):
        pts += [(x0 + 0.4 * i, 0.0), (x0 + 0.4 * i, w)]
    return SimpleNamespace(kind=stitches.SATIN, points=pts)


def test_column_widths_reads_the_crosses_of_each_column():
    runs = [_satin([1.0] * 6),                  # a 1.0 mm column
            _satin([0.6, 0.7, 0.5, 0.6, 0.6]),   # median 0.6
            _satin([0.2] * 3),                  # under 5 crosses: no column, but its cross counts
            SimpleNamespace(kind=stitches.FILL, points=[(0, 0), (0, 0.1)]),
            _satin([0.3] * 6, x0=50.0)]         # outside the box
    plan = SimpleNamespace(iter_runs=lambda: [(None, r) for r in runs])
    out = census.column_widths(plan, (-1, -1, 10, 5))
    assert out["col_min_mm"] == pytest.approx(0.6)
    assert out["col_median_mm"] == pytest.approx(0.8)
    assert out["cross_min_mm"] == pytest.approx(0.2)
    assert out["columns"] == 2
    none = census.column_widths(SimpleNamespace(iter_runs=lambda: []), (0, 0, 1, 1))
    assert none["columns"] == 0 and math.isnan(none["col_min_mm"])


def test_the_synthetic_60wt_off_row_at_three_millimetres():
    ref = json.loads((TESTDATA / "small_print_synthetic_ref.json").read_text())
    m, _ = census.cell(small_print.synthetic_text(), ref, 3.0, 60, False)
    assert (m["thread_wt"], m["floor"]) == (60, False)
    assert m["cap_mm"] == pytest.approx(3.0, abs=0.05)
    assert m["stitches"] == pytest.approx(532, abs=40)
    assert m["counters"] == 10 and 7 <= m["counters_shut"] <= 9
    assert m["counter_open"] == pytest.approx(0.34, abs=0.06)
    assert m["dust"] == pytest.approx(0.100, abs=0.02)
    assert m["col_min_mm"] == pytest.approx(0.64, abs=0.05)
    assert m["cross_min_mm"] >= 0.45
