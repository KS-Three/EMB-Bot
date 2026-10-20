"""The sew-out card v3 (`tools/sewout_card_v3.py`, 2026-10-13).

Kent's Hotel Fremont 81 mm questions on one 40 wt card: F3 (2.2 mm cap APA:
today / `small_print_floor` / `small_glyph_keep`), T (Fremont THE: today /
`lettering_words` + `lettering_word_tiers`), N (Fremont 1895: `small_glyph_keep`
OFF / ON) and G (card v2's forbid-gap block). These tests pin the card's block
list and arms, regenerate the card in a temp dir from the COMMITTED Fremont
cuts (`docs/sewout/card-v3-2026-10-13/cuts/`), and check the FILE against the
committed read-back. The cloth is Kent's to judge (ROADMAP gate 1); no engine
code is touched, and the Fremont replay itself is not re-run here (a digitize
is minutes: `--cut` makes the cuts, and the committed cuts carry the replay's
stitch counts, pinned below against #905's measured arms).

Counts that cannot move (blocks, colours, colour changes, pieces) are compared
exactly. Lengths, extents and stitch counts come out of the digitizer, whose
numerics differ a little per platform, so they are compared within a tolerance:
0.5 mm on a size, 3% on a count.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pystitch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import sewout_card_v3 as v3  # noqa: E402

COMMITTED = v3.REPO / "docs" / "sewout" / "card-v3-2026-10-13"

PIECES = {
    "F3:today", "F3:floor", "F3:keep",
    "T:today", "T:wordtier",
    "N:keep-off", "N:keep-on",
    "G:gap-off", "G:gap-0.4", "G:gap-0.8",
}


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardv3")
    rb = v3.generate(out, None, COMMITTED / "cuts", quiet=True)
    return out, rb


@pytest.fixture(scope="module")
def committed():
    return json.loads((COMMITTED / "readback-v3.json").read_text(encoding="utf-8"))


def test_the_block_list_and_arms_are_pinned():
    """Which blocks, which arms, in tooth order (1 tooth first). Changing one
    changes what Kent is asked to sew: say so in the PR, then edit this."""
    assert v3.BLOCKS == {
        "F3": ("today", "floor", "keep"),
        "T": ("today", "wordtier"),
        "N": ("keep-off", "keep-on"),
        "G": ("gap-off", "gap-0.4", "gap-0.8"),
    }
    assert {f"{b}:{a}" for b, arms in v3.BLOCKS.items() for a in arms} == PIECES
    # F3: three arms on the Hat profile, 2.2 mm cap, 40 wt.
    assert dict(v3.F3_ARMS) == {
        "today": {"small_print_floor": False, "small_glyph_keep": False},
        "floor": {"small_print_floor": True, "small_glyph_keep": False},
        "keep": {"small_print_floor": False, "small_glyph_keep": True},
    }
    assert (v3.F3_WORD, v3.F3_CAP_MM, v3.WT, v3.GARMENT) == ("APA", 2.2, 40, "hat_front")
    # T and N are cut from the Studio-request replay; `small_glyph_keep` is pinned
    # in every arm so a default flip cannot move the card. The skeleton-run arm
    # (`small_lettering_skeleton`) is NOT on the card: that branch has not merged.
    assert v3.CUT_ARMS == {
        "today": {"small_glyph_keep": False},
        "wordtier": {"small_glyph_keep": False, "lettering_words": True, "lettering_word_tiers": True},
        "keep": {"small_glyph_keep": True},
    }
    assert v3.CUT_BOXES == {"T": ("the", ("today", "wordtier")), "N": ("1895", ("today", "keep"))}
    assert "small_lettering_skeleton" not in json.dumps(v3.CUT_ARMS)


def test_the_committed_cuts_are_the_replay_that_905_measured():
    """The cuts carry the whole-design numbers of the replay they came from:
    #905's table for the same flags (main_81 15,306 stitches / 44 trims,
    wordtier_81 15,375 / 48, keep_81 15,611 / 46)."""
    want = {"today": (15306, 44), "wordtier": (15375, 48), "keep": (15611, 46)}
    for arm, (stitches, trims) in want.items():
        d = json.loads((COMMITTED / "cuts" / f"cut_{arm}.json").read_text(encoding="utf-8"))
        assert d["overrides"] == v3.CUT_ARMS[arm]
        assert d["width_mm"] == 81.0
        assert d["stitches_whole"] == pytest.approx(stitches, rel=0.01), arm
        assert d["trims_whole"] == pytest.approx(trims, abs=3), arm
        for box in ("T", "N"):
            assert d["boxes"][box]["runs"], (arm, box)


def test_the_cut_arms_differ_where_the_card_says_they_do():
    """A pair whose arms are the same thread is a blank test."""
    def pts(arm, box):
        d = v3.load_cut(COMMITTED / "cuts", arm, box)
        return [r["points"] for r in d["runs"]]
    assert pts("today", "T") != pts("wordtier", "T")
    assert pts("today", "N") != pts("keep", "N")


@pytest.mark.parametrize("key", ["blocks", "colours"])
def test_regenerated_readback_matches_the_committed_one(card, committed, key):
    _out, new = card
    assert new[key] == committed[key]
    assert new["blocks"] == 4 and new["colours"] == 3


def test_regenerated_readback_numbers(card, committed):
    _out, new = card
    old = committed
    assert new["colour_changes_file"] == new["colour_changes_plan"] == old["colour_changes_file"] == 2
    assert [s["thread"] for s in new["stops"]] == [s["thread"] for s in old["stops"]] == ["dark", "light", "dark"]
    assert new["max_needle_stitch_mm"] == pytest.approx(old["max_needle_stitch_mm"], abs=0.5)
    assert new["max_record_axis_mm"] == pytest.approx(old["max_record_axis_mm"], abs=0.2)
    for key in ("extent_mm", "x_range_mm", "y_range_mm"):
        assert new[key] == pytest.approx(old[key], abs=0.5), key
    assert new["stitches_file"] == pytest.approx(old["stitches_file"], rel=0.03)
    assert sorted(new["blocks_mm"]) == sorted(old["blocks_mm"]) == ["F3", "G", "N", "T"]
    assert set(new["pieces_mm"]) == set(old["pieces_mm"]) == PIECES


def test_the_hoop_fits_and_reads_back_whole(card):
    out, rb = card
    assert rb["within_hoop"] and max(rb["extent_mm"]) <= v3.HOOP_MM
    assert rb["stitches_file"] == rb["stitches_plan"] > 1000
    assert rb["max_needle_stitch_mm"] <= v3.MAX_RECORD_MM
    assert rb["max_record_axis_mm"] <= v3.MAX_RECORD_MM + 1e-6
    pat = pystitch.read_dst(str(out / rb["file"]))
    n = sum(1 for _x, _y, cmd in pat.stitches if (cmd & pystitch.COMMAND_MASK) == pystitch.STITCH)
    assert n == rb["stitches_file"]


def test_blocks_do_not_overlap_and_arms_sit_in_tooth_order(card):
    _out, rb = card
    boxes = sorted(rb["blocks_mm"].items())
    for k, (x0, y0, x1, y1) in boxes:
        assert -50 <= x0 < x1 <= 50 and -50 <= y0 < y1 <= 50, k
    for i, (ka, a) in enumerate(boxes):
        for kb, b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (ka, kb)
    p = rb["pieces_mm"]
    for blk, arms in v3.BLOCKS.items():
        xs = [p[f"{blk}:{a}"][0] for a in arms]
        assert xs == sorted(xs) and len(set(xs)) == len(xs), (blk, xs)


def test_every_arm_differs_from_the_first_in_its_block(card):
    """The cut pairs and G differ stitch for stitch; F3's arms are digitized
    by the engine, so at least one of its two candidates must move the thread
    (else the block is a blank test at this size)."""
    _out, rb = card
    n = rb["stitches_by_piece"]
    assert n["T:today"] != n["T:wordtier"]
    assert n["N:keep-off"] != n["N:keep-on"]
    assert n["G:gap-off"] != n["G:gap-0.8"]
    assert n["F3:today"] != n["F3:floor"] or n["F3:today"] != n["F3:keep"]
    pieces = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    assert pieces[("F3", "floor")]["small_print_floor"] and not pieces[("F3", "today")]["small_print_floor"]
    assert pieces[("F3", "keep")]["small_glyph_keep"] and not pieces[("F3", "today")]["small_glyph_keep"]
    assert pieces[("G", "gap-0.8")]["forbid_gap_mm"] == 0.8 and pieces[("G", "gap-off")]["forbid_gap_mm"] is None


def test_the_index_strips_and_labels_hold_the_one_millimetre_floor(card):
    _out, rb = card
    assert not [k for k in rb["under_1mm_by_piece"] if k.endswith(":strips")], rb["under_1mm_by_piece"]


def test_the_earlier_cards_are_not_overwritten(card):
    """v3 writes beside v1 and v2, never over them."""
    assert COMMITTED.name == "card-v3-2026-10-13"
    assert (COMMITTED.parent / "hairline-card-2026-10-12" / "hairline_card_40wt.dst").exists()
    assert (COMMITTED.parent / "card-v2-2026-10-13" / "card_v2_40wt.dst").exists()


def test_the_readout_sheet_names_every_block_and_arm():
    sheet = (COMMITTED / "scoring-sheet-v3.md").read_text(encoding="utf-8")
    for needle in ("## F3", "## T", "## N", "## G", "small_print_floor", "small_glyph_keep",
                   "lettering_words", "lettering_word_tiers", "forbid_gap_mm", "1 tooth", "2 teeth", "3 teeth"):
        assert needle in sheet, needle
