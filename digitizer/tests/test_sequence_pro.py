"""`tools/sequence_pro.py` -- the sew-order reader, pinned on hand-built DSTs.

Every file here is written by hand (`tests/proloop_synth.write_pattern`), so
the test knows the order, the pieces and the cuts. The reader must find them
the same way on either side of a pro/ours pair.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import sequence_pro as sp  # noqa: E402

from .proloop_synth import fill_passes, write_pattern  # noqa: E402

GROUND = (40, 40, 40)
INK = (200, 30, 30)


def _piece(x0, y0=0.0, w=4.0, h=6.0):
    """One letter-sized fill box as ONE needle-down pass (rows joined)."""
    return [p for row in fill_passes(x0, y0, w, h) for p in row]


def _read(tmp_path, blocks, name="t.dst"):
    return sp.read_file(write_pattern(tmp_path / name, blocks))


def test_five_letters_centre_out_is_the_cap_rule(tmp_path):
    """A row of five letters 6 mm apart, sewn the pro's way: the middle one,
    the left side outward, then the right side outward."""
    xs = {0: 0.0, 1: 10.0, 2: 20.0, 3: 30.0, 4: 40.0}
    order = [2, 1, 0, 3, 4]
    r = _read(tmp_path, [(INK, [_piece(xs[i]) for i in order])])
    b = r["blocks"][0]
    assert b["pieces"] == 5 and b["visits"] == 5 and b["revisits"] == 0
    assert b["trims"] == 4 and b["inter_trims"] == 4
    assert b["order_gap_mm"] == pytest.approx(b["centre_out_gap_mm"], abs=0.3)
    # the fly-back from the left end to the right of centre costs more than
    # stage 7's sweep (nearest-neighbour from the end letter)
    assert b["order_gap_mm"] > b["sweep_gap_mm"] + 5.0
    # every gap is 6 mm on bare fabric: no order sews any of them through
    assert b["min_inter_trims"] == 4 and b["reach_first_trims"] == 4
    assert b["cut_skipped_reach"] == 0 and b["cut_dead_end"] == 4
    assert b["line_steps"] == 4 and b["line_ltr"] == 2


def test_left_to_right_reads_as_left_to_right(tmp_path):
    r = _read(tmp_path, [(INK, [_piece(x) for x in (0.0, 10.0, 20.0)])])
    b = r["blocks"][0]
    assert b["line_steps"] == 2 and b["line_ltr"] == 2
    assert b["order_gap_mm"] == pytest.approx(b["sweep_gap_mm"], abs=0.3)


def test_a_short_gap_is_sewn_through_only_on_work(tmp_path):
    """Two letters 2 mm apart: on bare fabric the hop is still a cut (the pro
    never lays thread across bare fabric); on a ground sewn underneath it is
    within reach, so no order needs a cut there."""
    bare = _read(tmp_path, [(INK, [_piece(0.0), _piece(6.0)])], "bare.dst")
    assert bare["blocks"][0]["min_inter_trims"] == 1
    on_ground = _read(tmp_path, [(GROUND, [[p for row in fill_passes(-3, -3, 16, 12) for p in row]]),
                                 (INK, [_piece(0.0), _piece(6.0)])], "ground.dst")
    ink = on_ground["blocks"][1]
    assert ink["min_inter_trims"] == 0 and ink["reach_first_trims"] == 0
    assert ink["inter_trims"] == 1 and ink["cut_next_in_reach"] == 1
    assert on_ground["total"]["colour_changes"] == 1


def test_a_reachable_letter_passed_over_is_an_order_cut(tmp_path):
    """A, B 2 mm apart on a ground, C 20 mm away; sewn A, C, B. Leaving A
    passes over B (in reach, unsewn): an ORDER cut. Leaving C nothing unsewn
    is in reach: a dead end."""
    ground = [[p for row in fill_passes(-3, -3, 40, 12) for p in row]]
    r = _read(tmp_path, [(GROUND, ground),
                         (INK, [_piece(0.0), _piece(26.0), _piece(6.0)])])
    ink = r["blocks"][1]
    assert ink["inter_trims"] == 2
    assert ink["cut_skipped_reach"] == 1 and ink["cut_dead_end"] == 1
    assert ink["reach_first_trims"] == 1


def test_a_piece_left_and_come_back_to_is_a_revisit(tmp_path):
    left, right = _piece(0.0), _piece(10.0)
    half = len(left) // 2
    r = _read(tmp_path, [(INK, [left[:half], right, left[half:]])])
    b = r["blocks"][0]
    assert b["pieces"] == 2 and b["visits"] == 3 and b["revisits"] == 1


def test_start_and_end_are_fractions_of_the_design(tmp_path):
    r = _read(tmp_path, [(INK, [_piece(20.0), _piece(0.0), _piece(40.0)])])
    b = r["blocks"][0]
    assert 0.45 < b["start"][0] < 0.55
    assert b["end"][0] > 0.9
