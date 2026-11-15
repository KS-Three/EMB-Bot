"""A Cancel lands inside stage 0's colour-mass k-means and the script lane's
station loop, not after them.

Measured 2026-11-14 (`tools/flip_timing.py`, the timing pass over the day's
flips): on Tires at 114 mm the two longest stretches of a digitize with no
`deadline.check` were

* before stage 0's first check, `stage0_classify._unique_color_mass`:
  3.7 of classify's 6.4 s in `_assign`, nine calls (one per k-means
  iteration), each a loop over 200,000-pixel chunks;
* stage 7, from the per-shape check to the satin rail push:
  `script_strokes.script_columns`, 6.1 s on one script word, 3.3 of it in
  `_stations`' boundary reads.

A check reads a clock and moves no number, so a run that is not cancelled is
identical with or without the recorder (pinned below for both).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core import deadline  # noqa: E402


class _Recorder:
    def __init__(self, real):
        self.real, self.labels = real, []

    def __call__(self, stage: str) -> None:
        self.labels.append(stage)
        self.real(stage)


def _recorded(monkeypatch):
    rec = _Recorder(deadline.check)
    monkeypatch.setattr(deadline, "check", rec)
    return rec


def test_stage0_colour_mass_has_a_seam_and_moves_nothing(monkeypatch):
    from digitizer_core import stage0_classify as s0
    rng = np.random.default_rng(7)
    rgb = rng.integers(0, 255, (300, 400, 3), dtype=np.uint8)
    rgb[:, :200] = (20, 40, 200)
    fg = np.ones((300, 400), bool)
    before = s0._unique_color_mass(rgb, fg, 0)
    rec = _recorded(monkeypatch)
    after = s0._unique_color_mass(rgb, fg, 0)
    assert after == before
    assert rec.labels.count("stage 0 colour mass") >= 2


def test_script_stations_have_a_seam_and_move_nothing(monkeypatch):
    from digitizer_core import script_strokes as ss
    # a script-like stroke: a thick S, 2 mm wide
    t = np.linspace(0, 2 * np.pi, 120)
    word = LineString(np.column_stack([t * 4.0, 3.0 * np.sin(t)])).buffer(1.0)
    before = ss.script_columns(word, 0.4)
    rec = _recorded(monkeypatch)
    after = ss.script_columns(word, 0.4)
    assert [c.stations for c in after[0]] == [c.stations for c in before[0]]
    assert rec.labels.count("script stations") >= 10
    assert "script pen strokes" in rec.labels
