"""`tools/layer_census.py` -- where a file sews one colour ON another, pinned
on hand-built DSTs (`tests/proloop_synth.write_pattern`), so the test knows
every piece's answer.

A 20 x 20 mm ground and a 6 x 6 mm badge in its middle, built three ways:
the ground sewn solid under the badge (layered, the professional's habit),
the ground with a hole the badge fills (knock-out), and the badge sewn first
with the ground round it. A side-by-side neighbour is the piece no outline
holds.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import layer_census as lc  # noqa: E402

from .proloop_synth import fill_passes, write_pattern  # noqa: E402

GROUND = (40, 40, 40)
BADGE = (230, 120, 20)
SIDE = (20, 60, 200)


def _box(x0, y0, w, h):
    """A fill box as one needle-down pass (rows joined)."""
    return [p for row in fill_passes(x0, y0, w, h) for p in row]


def _ground_with_hole():
    """The 20 x 20 ground as four bands round a 6 x 6 hole at (7, 7)."""
    return [_box(0, 0, 20, 7), _box(0, 13, 20, 7), _box(0, 7, 7, 6), _box(13, 7, 7, 6)]


def _read(tmp_path, name, blocks, **kw):
    return lc.read(write_pattern(tmp_path / name, blocks), [f"#{r:02x}{g:02x}{b:02x}" for (r, g, b), _ in blocks],
                   **kw)


def _only(r, block):
    (p,) = [p for p in r["pieces"] if p["block"] == block]
    return p


def test_a_badge_on_a_solid_ground_is_on_and_inside(tmp_path):
    r = _read(tmp_path, "layered.dst", [(GROUND, [_box(0, 0, 20, 20)]), (BADGE, [_box(7, 7, 6, 6)])])
    p = _only(r, 1)
    assert p["label"] == "on" and p["on"] == pytest.approx(1.0)
    assert p["inside"] >= lc.CONTAIN and p["host"] == 0
    # the 6 x 6 badge drawn a thread wide (+0.2 mm a side), less the half
    # millimetre a side the reading erodes: 5.4 x 5.4
    assert r["layered_mm2"] == pytest.approx(5.4 * 5.4, rel=0.1)
    assert r["under_by_colour"] == {"#282828": pytest.approx(r["layered_mm2"])}


def test_a_badge_in_the_grounds_hole_is_knocked_out_but_still_inside(tmp_path):
    r = _read(tmp_path, "knock.dst", [(GROUND, _ground_with_hole()), (BADGE, [_box(7, 7, 6, 6)])])
    p = _only(r, 1)
    assert p["label"] == "off" and p["on"] == pytest.approx(0.0, abs=0.05)
    assert p["inside"] >= lc.CONTAIN        # the outline closes the hole
    assert r["layered_mm2"] == pytest.approx(0.0, abs=0.5)


def test_a_badge_sewn_first_is_not_read_as_layered(tmp_path):
    r = _read(tmp_path, "first.dst", [(BADGE, [_box(7, 7, 6, 6)]), (GROUND, _ground_with_hole())])
    assert all(p["block"] == 1 for p in r["pieces"])     # only the ground meets an earlier colour
    assert all(p["label"] == "off" for p in r["pieces"])
    assert r["layered_mm2"] == pytest.approx(0.0, abs=0.5)


def test_a_side_by_side_neighbour_is_outside(tmp_path):
    r = _read(tmp_path, "side.dst", [(GROUND, [_box(0, 0, 20, 20)]), (SIDE, [_box(20, 0, 10, 20)])])
    p = _only(r, 1)
    assert p["inside"] < lc.CONTAIN and p["label"] == "off"


def test_a_same_colour_revisit_is_not_layering_but_counts_as_a_revisit(tmp_path):
    r = _read(tmp_path, "revisit.dst", [(GROUND, [_box(0, 0, 20, 20)]), (BADGE, [_box(7, 7, 6, 6)]),
                                        (GROUND, [_box(8, 8, 4, 4)])])
    assert r["blocks"] == 3 and r["cones"] == 2
    (rv,) = r["revisits"]
    assert rv["block"] == 2 and rv["after"] == 0
    assert rv["covered_between_mm2"] > 10          # the badge sewed over the ground in between
    assert all(p["block"] != 2 or p["host"] != 0 for p in r["pieces"])   # own colour is never a host


def test_a_beanie_knockdown_is_no_ground(tmp_path):
    blocks = [((250, 250, 250), [_box(-1, -1, 22, 22)]), (GROUND, [_box(0, 0, 20, 20)]),
              (BADGE, [_box(7, 7, 6, 6)])]
    r = _read(tmp_path, "beanie.dst", blocks, beanie=True)
    assert r["knockdown"] and r["blocks"] == 2 and r["cones"] == 2
    assert {p["block"] for p in r["pieces"]} == {2}
    assert r["under_by_colour"].keys() == {"#282828"}


def test_kappa():
    assert lc.kappa([]) is None
    assert lc.kappa([(True, True), (False, False)]) == pytest.approx(1.0)
    assert lc.kappa([(True, True)] * 3) is None            # one label on both sides: no chance correction
    # 4 agree of 6, each side half True: po 0.667, pe 0.5
    pairs = [(True, True), (True, True), (False, False), (False, False), (True, False), (False, True)]
    assert lc.kappa(pairs) == pytest.approx(1 / 3)


def test_compare_reads_the_same_place_in_both_files(tmp_path):
    layered = [(GROUND, [_box(0, 0, 20, 20)]), (BADGE, [_box(7, 7, 6, 6)]), (SIDE, [_box(1, 1, 4, 4)])]
    knock = [(GROUND, _ground_with_hole()), (BADGE, [_box(7, 7, 6, 6)]), (SIDE, [_box(1, 1, 4, 4)])]
    a = _read(tmp_path, "a.dst", layered, keep=True)
    b = _read(tmp_path, "b.dst", knock, keep=True)
    same = lc.compare(a, a)
    assert same["agree"] == same["n"] == 2
    c = lc.compare(b, a)                      # ours knocked out, his layered
    by_block = {q["block"]: q for q in c["rows"]}
    assert by_block[1]["ours"] == "off" and by_block[1]["pro"] == "on"
    assert by_block[2]["ours"] == "on" and by_block[2]["pro"] == "on"
    assert c["agree"] == 1 and c["n"] == 2
