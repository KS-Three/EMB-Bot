"""The hairline sew-out card (`tools/hairline_card.py`, 2026-10-12).

Two hoops, blocks A-E, each file written through the service's export path
(pystitch) and read back. Every number on the card is a candidate until Kent
sews it (ROADMAP gate 1); these tests check the FILES, not the cloth.
"""
from __future__ import annotations

import math

import pystitch
import pytest

from digitizer_core import machine
from digitizer_core.export import plan_to_pattern
from digitizer_service import formats
from tools import hairline_card as hc


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("card")
    out = {}
    for wt in hc.WEIGHTS:
        plan, card, _extra = hc.build(wt, tmp)
        pattern = plan_to_pattern(plan)
        pattern.metadata("name", f"HAIR{wt}WT")
        path = tmp / f"hairline_card_{wt}wt.dst"
        path.write_bytes(formats.write(pattern, "dst"))
        out[wt] = (plan, card, path, hc.readback(path, plan, wt))
    return out


@pytest.mark.parametrize("wt", hc.WEIGHTS)
def test_each_hoop_fits_100_by_100_and_reads_back_whole(built, wt):
    plan, _card, _path, rb = built[wt]
    assert rb["within_hoop"] and max(rb["extent_mm"]) <= hc.HOOP_MM
    assert rb["stitches_file"] == rb["stitches_plan"] > 1000
    # Three stops: the ground, then dark, then light.
    assert rb["colour_changes_file"] == rb["colour_changes_plan"] == 2
    assert [b.thread_index for b in plan.blocks] == [hc.GROUND, hc.DARK, hc.LIGHT]


@pytest.mark.parametrize("wt", hc.WEIGHTS)
def test_no_short_stitch_outside_the_places_the_card_expects_one(built, wt):
    """Under 1.0 mm only where a block tests it (A's 0.73 lines, C's 0.6 / 0.8
    columns), where the engine does it anyway (D's lettering, E's tatami row
    turns), or as the existing 0.8 mm lock legs."""
    _plan, _card, _path, rb = built[wt]
    assert rb["short_unexpected"] == 0, rb["short_by_block"]
    assert set(rb["short_by_block"]) <= set(hc.EXPECTED_SHORT)
    # The lines at 1.0 / 1.5 / 2.0 mm and the combs hold the floor.
    assert "A:other" not in rb["short_by_block"] and "B" not in rb["short_by_block"]
    assert rb["lock_legs_0p8"] > 0


def test_the_blocks_sit_inside_the_hoop_and_do_not_overlap(built):
    boxes = built[40][1].boxes
    assert set(boxes) == set("ABCDE")
    items = sorted(boxes.items())
    for k, (x0, y0, x1, y1) in items:
        assert -50 <= x0 < x1 <= 50 and -50 <= y0 < y1 <= 50, k
    for i, (ka, a) in enumerate(items):
        for kb, b in items[i + 1:]:
            apart = a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1]
            assert apart, (ka, kb)


def test_the_block_letters_are_sewn_as_runs_one_per_block(built):
    plan = built[40][0]
    letters = {r.shape_id.split(":")[0] for _b, r in plan.iter_runs() if r.shape_id.endswith(":index")}
    assert letters == set("ABCDE")


def test_the_60_weight_hoop_changes_the_satin_spacing_and_the_lettering_only(built):
    """Same geometry for A, B and E in both hoops; C's columns sew at the
    weight's own spacing (0.40 / 0.32), D's lettering through `thread_wt`."""
    def by_block(plan):
        out = {}
        for _b, r in plan.iter_runs():
            out.setdefault(r.shape_id.split(":")[0], []).append((r.shape_id, [tuple(p) for p in r.points]))
        return out
    a, b = by_block(built[40][0]), by_block(built[60][0])
    for blk in "ABE":
        assert [(s, [(round(x, 6), round(y, 6)) for x, y in p]) for s, p in a[blk]] == \
               [(s, [(round(x, 6), round(y, 6)) for x, y in p]) for s, p in b[blk]], blk
    n40 = sum(len(p) for s, p in a["C"] if ":col:" in s)
    n60 = sum(len(p) for s, p in b["C"] if ":col:" in s)
    assert n60 / n40 == pytest.approx(0.40 / 0.32, rel=0.1)
    assert machine.thread_profile(40).satin_spacing_mm == pytest.approx(0.40)
    assert machine.thread_profile(60).satin_spacing_mm == pytest.approx(0.32)
    assert a["D"] != b["D"]


def test_the_stitch_lengths_on_block_A_are_the_ones_the_card_names(built):
    plan = built[40][0]
    for L in (1.0, 1.5, 2.0):
        for _b, r in plan.iter_runs():
            if r.shape_id.startswith("A:straight:one:") and r.shape_id.endswith(f":{L}"):
                core = hc.strip_ties(r.points)
                steps = [math.dist(p, q) for p, q in zip(core, core[1:])]
                assert min(steps) >= L - 1e-6 and max(steps) <= L * 1.35, (L, min(steps), max(steps))
    pts = next(r.points for _b, r in plan.iter_runs() if r.shape_id == "A:straight:one:0.73")
    core = hc.strip_ties(pts)
    assert sum(math.dist(p, q) for p, q in zip(core, core[1:])) / (len(core) - 1) == pytest.approx(0.73, abs=0.03)


@pytest.mark.parametrize("wt", hc.WEIGHTS)
def test_the_file_is_the_trustworthy_path_not_the_browser_codec(built, wt):
    """pystitch reads its own DST back, and the plan's own extent agrees: the
    standard nibble order, not `src/dst.js`'s old transposed one."""
    plan, _card, path, rb = built[wt]
    pat = pystitch.read_dst(str(path))
    xs = [x / 10 for x, _y, c in pat.stitches if c & pystitch.COMMAND_MASK == pystitch.STITCH]
    ys = [y / 10 for _x, y, c in pat.stitches if c & pystitch.COMMAND_MASK == pystitch.STITCH]
    assert (max(xs) - min(xs), max(ys) - min(ys)) == pytest.approx(tuple(rb["plan_extent_mm"]), abs=0.15)
    # The card is wider than it is tall (94 x 82): a transposed file would not be.
    assert max(xs) - min(xs) > max(ys) - min(ys)
