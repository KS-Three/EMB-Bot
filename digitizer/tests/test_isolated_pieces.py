"""`tools/isolated_pieces.py` -- the pieces no tour reaches without a cut, pinned on hand-built DSTs.

Every file here is written by hand (`tests/proloop_synth.write_pattern`), so
the test knows the pieces, the gaps and which ones stand alone. The reader
must find them by `sequence_pro`'s own rules, and read the pro's file at the
same place the same way.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import isolated_pieces as ip  # noqa: E402
from tools import sequence_pro as sp  # noqa: E402
from tools.pro_parity.pairframe import Reg  # noqa: E402

from .proloop_synth import fill_passes, satin_pass, write_pattern  # noqa: E402

GROUND = (40, 40, 40)
INK = (200, 30, 30)
IDENTITY = Reg(scale=1.0, flip_y=False, dx=0.0, dy=0.0, iou=1.0)


def _box(x0, y0=0.0, w=4.0, h=6.0):
    """One fill box as ONE needle-down pass (rows joined)."""
    return [p for row in fill_passes(x0, y0, w, h) for p in row]


def _read(tmp_path, blocks, name="t.dst"):
    return ip.read_file(write_pattern(tmp_path / name, blocks))


def test_two_boxes_on_bare_fabric_one_stands_alone(tmp_path):
    """Two boxes 2 mm apart on bare fabric: the hop is a cut whatever the
    order, so one of them is isolated; its gap is read, and is not on thread."""
    r = _read(tmp_path, [(INK, [_box(0.0), _box(6.0, w=1.0)])])
    t = ip.totals(r)
    assert t == {"pieces": 2, "blocks": 1, "entries": 2, "isolated": 1, "floor_cuts": 1, "greedy_cuts": 1}
    row = r["blocks"][0]["isolated"][0]
    # the body is the larger box: the 1 mm strip is the isolated one
    assert row["area_mm2"] < 15.0
    assert row["near_mm"] == pytest.approx(2.0, abs=0.3)
    assert row["gap_on_thread"] is False
    # footprint width: the strip's needle span plus one thread
    assert row["width_mm"] == pytest.approx(1.0 + sp.THREAD_MM, abs=0.3)


def test_on_a_ground_nothing_stands_alone(tmp_path):
    ground = [[p for row in fill_passes(-3, -3, 16, 12) for p in row]]
    r = _read(tmp_path, [(GROUND, ground), (INK, [_box(0.0), _box(6.0)])])
    assert r["blocks"][1]["isolated"] == []
    assert ip.totals(r)["floor_cuts"] == 0


def test_greedy_matches_sequence_pro(tmp_path):
    """The greedy tour is `sequence_pro`'s `reach_first_trims`, piece for piece."""
    ground = [[p for row in fill_passes(-3, -3, 40, 12) for p in row]]
    blocks = [(GROUND, ground), (INK, [_box(0.0), _box(26.0), _box(6.0), _box(50.0)])]
    path = write_pattern(tmp_path / "g.dst", blocks)
    mine = ip.read_file(path)
    theirs = sp.read_file(path)
    assert ip.totals(mine)["greedy_cuts"] == theirs["total"]["reach_first_trims"]
    assert ip.totals(mine)["floor_cuts"] == theirs["total"]["min_inter_trims"]
    assert ip.totals(mine)["isolated"] == 2     # the 26 mm box joins nothing; nor does the 50 mm one


@pytest.mark.parametrize("pro_blocks, verdict", [
    # he sews only the body: nothing of his where our strip is
    ([(INK, [_box(0.0)])], "drops"),
    # one box of his spans our strip and the body beside it
    ([(INK, [_box(0.0, w=7.0)])], "merges"),
    # he sews the strip on its own, across bare fabric
    ([(INK, [_box(0.0), _box(6.0, w=1.0)])], "alone"),
    # ...or on his ground, within reach of the body
    ([(GROUND, [[p for row in fill_passes(-3, -3, 16, 12) for p in row]]),
      (INK, [_box(0.0), _box(6.0, w=1.0)])], "bridges"),
])
def test_pro_at_the_same_place(tmp_path, pro_blocks, verdict):
    ours = _read(tmp_path, [(INK, [_box(0.0), _box(6.0, w=1.0)])], "ours.dst")
    pro = _read(tmp_path, pro_blocks, "pro.dst")
    ip.pro_at(ours, pro, IDENTITY)
    (row,) = ours["blocks"][0]["isolated"]
    assert row["pro"]["verdict"] == verdict


@pytest.mark.parametrize("width, angle", [(0.7, 0.0), (1.5, 30.0), (3.0, 75.0)])
def test_a_satin_column_reads_its_own_swing(width, angle):
    """The census's `satin_swings` reads a column's needle swing ACROSS it,
    whatever its slant and pitch -- not the step length, which also carries
    the advance along the column. Pitch 0.2 per step: the pro's satins
    cross each rail every ~0.37 mm (`pro_measured_values`)."""
    pts = satin_pass(0.0, 0.0, 12.0, width, pitch=0.2, angle_deg=angle)
    mv = [{"p": p, "up": i == 0, "trim": False} for i, p in enumerate(pts)]
    (swing,) = ip.satin_swings(mv, range(len(mv)))
    assert swing == pytest.approx(width, abs=0.03)


def test_the_census_cannot_see_a_column_narrower_than_its_floor():
    """At that pitch a step's reversal reads under -0.7 only while the column
    is wider than ~0.45 mm: narrower, it is a run to this reader. The pro's
    narrowest column read is 0.54 mm, above that floor, so nothing between
    the floor and `PRO_MIN_SWING_MM` is hidden from the census."""
    for width, seen in ((0.40, False), (0.50, True)):
        pts = satin_pass(0.0, 0.0, 12.0, width, pitch=0.2)
        mv = [{"p": p, "up": i == 0, "trim": False} for i, p in enumerate(pts)]
        assert bool(ip.satin_swings(mv, range(len(mv)))) is seen
