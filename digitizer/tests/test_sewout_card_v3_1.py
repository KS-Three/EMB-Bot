"""The sew-out card v3.1 (`tools/sewout_card_v3_1.py`, 2026-10-13).

Card v3 plus the small-lettering skeleton arms (#913): block S (the Fremont
tagline, today / skeleton at the default floor / skeleton at 0.73 mm), block E2
(enthusiast's ENTERPRISES INC, today / skeleton at 0.73 mm), and a pair of
lettering-ends VERIFICATION blocks (X: Fremont E, M->O, N; B: Becker MARINE;
`lettering_columns_square_ends` + `lettering_columns_inside_connectors` OFF /
ON). F3, T, N and G are v3's, unchanged. These tests pin the block list and
arms, regenerate the card in a temp dir from the COMMITTED cuts
(`docs/sewout/card-v3-2026-10-13/cuts/cut31_*.json`), and check the FILE
against the committed read-back, piece by piece. The cloth is Kent's to judge
(ROADMAP gate 1); no engine code is touched and the digitizes themselves are
not re-run here (minutes each: `--cut` makes the cuts, and the committed cuts
carry the whole-design stitch and trim counts, pinned below against #913 and
#912).

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

from tools import sewout_card_v3_1 as v31  # noqa: E402

COMMITTED = v31.v3.REPO / "docs" / "sewout" / "card-v3-2026-10-13"
CUTS = COMMITTED / "cuts"

PIECES = {
    "F3:today", "F3:floor", "F3:keep",
    "T:today", "T:wordtier",
    "N:keep-off", "N:keep-on",
    "G:gap-off", "G:gap-0.4", "G:gap-0.8",
    "S:today", "S:floor-1.0", "S:floor-0.73",
    "E2:today", "E2:floor-0.73",
    "X:ends-off", "X:ends-on",
    "B:ends-off", "B:ends-on",
}


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardv31")
    rb = v31.generate(out, None, CUTS, quiet=True)
    return out, rb


@pytest.fixture(scope="module")
def committed():
    return json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))


def test_the_block_list_and_arms_are_pinned():
    """Which blocks, which arms, in tooth order (1 tooth first). Changing one
    changes what Kent is asked to sew: say so in the PR, then edit this."""
    assert v31.BLOCKS == {
        "F3": ("today", "floor", "keep"),
        "T": ("today", "wordtier"),
        "N": ("keep-off", "keep-on"),
        "G": ("gap-off", "gap-0.4", "gap-0.8"),
        "S": ("today", "floor-1.0", "floor-0.73"),
        "E2": ("today", "floor-0.73"),
        "X": ("ends-off", "ends-on"),
        "B": ("ends-off", "ends-on"),
    }
    assert {f"{b}:{a}" for b, arms in v31.BLOCKS.items() for a in arms} == PIECES
    # F3, T, N, G are v3's, unchanged
    for blk in ("F3", "T", "N", "G"):
        assert v31.BLOCKS[blk] == v31.v3.BLOCKS[blk]
    assert (v31.WT, v31.v3.GARMENT) == (40, "hat_front")


def test_the_arm_flags_are_pinned():
    """Every flag that could move a piece is pinned OFF in every arm, so a
    default flip (the ends flags are being turned ON elsewhere) cannot move the
    card; an arm changes only what it names."""
    pins = v31.PINS
    for key in ("lettering_columns_square_ends", "lettering_columns_inside_connectors",
                "small_lettering_skeleton", "small_glyph_keep", "lettering_words", "lettering_word_tiers",
                "small_text_true_size"):
        assert pins[key] is False, key
    for key in ("small_lettering_skeleton_floor_mm", "small_text_cap_mm", "small_text_restore_mm",
                "bean_letter_max_stroke_mm", "bean_letter_stitch_mm"):      # #909 and #911 OFF
        assert pins[key] is None, key
    assert v31.CUT_ARMS["today"] == pins
    assert v31.CUT_ARMS["skel"] == {**pins, "small_lettering_skeleton": True}
    assert v31.CUT_ARMS["skel073"] == {**pins, "small_lettering_skeleton": True,
                                       "small_lettering_skeleton_floor_mm": 0.73}
    assert v31.CUT_ARMS["ends_on"] == {**pins, "lettering_columns_square_ends": True,
                                       "lettering_columns_inside_connectors": True}
    assert v31.ENT_ARMS["ent_today"] == pins
    assert v31.ENT_ARMS["ent_skel073"] == v31.CUT_ARMS["skel073"]
    assert v31.BECKER_ARMS == {"becker_off": pins, "becker_on": v31.CUT_ARMS["ends_on"]}
    # where each new arm comes from
    assert v31.SOURCES == {
        "S": {"today": ("today", ["S"]), "floor-1.0": ("skel", ["S"]), "floor-0.73": ("skel073", ["S"])},
        "E2": {"today": ("ent_today", ["E2"]), "floor-0.73": ("ent_skel073", ["E2"])},
        "X": {"ends-off": ("today", ["E", "MON"]), "ends-on": ("ends_on", ["E", "MON"])},
        "B": {"ends-off": ("becker_off", ["B"]), "ends-on": ("becker_on", ["B"])},
    }


def test_the_committed_cuts_are_the_replays_that_913_and_912_measured():
    """Each cut file records the flags it was made with and the whole-design
    numbers of the digitize it came from: #913's table for the tagline arms
    (main 15,306 / 44, ON 1.0 15,124 / 44, ON 0.73 14,886 / 44; enthusiast 2,428
    -> 2,102 / 8), #912's for the ends (Fremont ON 15,320 / 45; Becker 6,011 / 22
    -> 6,150 / 25)."""
    allarms = {**v31.CUT_ARMS, **v31.ENT_ARMS, **v31.BECKER_ARMS}
    want = {**v31.FREMONT_TOTALS, **v31.ENT_TOTALS, **v31.BECKER_TOTALS}
    assert set(want) == set(allarms) == set(v31.ALL_CUTS)
    for arm, (stitches, trims) in want.items():
        d = v31.load_cut_file(CUTS, arm)
        assert d["overrides"] == allarms[arm], arm
        assert d["stitches_whole"] == pytest.approx(stitches, rel=0.01), arm
        assert d["trims_whole"] == pytest.approx(trims, abs=3), arm
    for arm in v31.CUT_ARMS:
        assert v31.load_cut_file(CUTS, arm)["width_mm"] == 81.0
    for arm in v31.ENT_ARMS:
        assert v31.load_cut_file(CUTS, arm)["width_mm"] == 80.0
    # the enthusiast tier is offered 14 letters and sews 11 at 0.73 (#913)
    d = v31.load_cut_file(CUTS, "ent_skel073")
    assert (d["offered"], d["skeleton_sewn"]) == (14, 11)
    assert v31.load_cut_file(CUTS, "ent_today")["offered"] == 0


def test_the_new_arms_differ_where_the_card_says_they_do():
    """A pair whose arms are the same thread is a blank test."""
    def pts(arm, box):
        return [r["points"] for r in v31.load_cut(CUTS, arm, box)["runs"]]
    assert pts("today", "S") != pts("skel", "S") != pts("skel073", "S")
    assert pts("skel", "S") != pts("skel073", "S")
    assert pts("ent_today", "E2") != pts("ent_skel073", "E2")
    for box in ("E", "MON"):
        assert pts("today", box) != pts("ends_on", box), box
    assert pts("becker_off", "B") != pts("becker_on", "B")
    # both Fremont ends arms hold the same letters
    for box, ids in v31.ENDS_SHAPES.items():
        for arm in ("today", "ends_on"):
            assert {r["shape_id"] for r in v31.load_cut(CUTS, arm, box)["runs"]} == set(ids)


def test_the_skeleton_arm_is_dropped_from_block_t_because_the_cuts_prove_it_a_duplicate():
    """#913: THE is unaffected (its T is declined on width). The THE box cut from
    each skeleton arm is point-for-point today's, and today's is v3's own T cut."""
    got = v31.the_is_unaffected(CUTS)
    assert got["skel_same_as_today"] and got["skel073_same_as_today"] and got["today_same_as_v3_cut"], got
    assert "small_lettering_skeleton" not in json.dumps(v31.v3.CUT_ARMS)       # v3's T arms are untouched


@pytest.mark.parametrize("key", ["blocks", "colours"])
def test_regenerated_readback_matches_the_committed_one(card, committed, key):
    _out, new = card
    assert new[key] == committed[key]
    assert new["blocks"] == 8 and new["colours"] == 3


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
    assert new["trims"] == pytest.approx(old["trims"], abs=3)
    assert sorted(new["blocks_mm"]) == sorted(old["blocks_mm"]) == ["B", "E2", "F3", "G", "N", "S", "T", "X"]
    assert set(new["pieces_mm"]) == set(old["pieces_mm"]) == PIECES


def test_the_hoop_fits_and_reads_back_whole(card):
    out, rb = card
    assert rb["within_hoop"] and max(rb["extent_mm"]) <= v31.HOOP_MM
    assert rb["stitches_file"] == rb["stitches_plan"] > 1000
    assert rb["max_needle_stitch_mm"] <= v31.MAX_RECORD_MM
    assert rb["max_record_axis_mm"] <= v31.MAX_RECORD_MM + 1e-6
    pat = pystitch.read_dst(str(out / rb["file"]))
    n = sum(1 for _x, _y, cmd in pat.stitches if (cmd & pystitch.COMMAND_MASK) == pystitch.STITCH)
    assert n == rb["stitches_file"]


def test_every_piece_reads_back_from_the_decoded_file(card):
    """Read-back verified, piece by piece: decode the written DST, and each arm's
    stitch count and extent equal those of the in-memory pattern it was written
    from (within a stitch or two and 0.2 mm for the format's 0.1 mm grid)."""
    _out, rb = card
    assert set(rb["decoded_pieces"]) == PIECES
    for key, d in rb["decoded_pieces"].items():
        assert d["file"]["stitches"] > 0, key
        assert d["file"]["stitches"] == pytest.approx(d["plan"]["stitches"], abs=3), key
        assert d["file"]["w"] == pytest.approx(d["plan"]["w"], abs=0.2), key
        assert d["file"]["h"] == pytest.approx(d["plan"]["h"], abs=0.2), key
        # the extent of the stitches is the arm's box, to the margin the owner rule grows it by
        assert d["file"]["w"] <= d["box"][0] + 0.7 and d["file"]["h"] <= d["box"][1] + 0.7, key


def test_blocks_do_not_overlap_and_arms_sit_in_tooth_order(card):
    _out, rb = card
    boxes = sorted(rb["blocks_mm"].items())
    for k, (x0, y0, x1, y1) in boxes:
        assert -50 <= x0 < x1 <= 50 and -50 <= y0 < y1 <= 50, k
    for i, (ka, a) in enumerate(boxes):
        for kb, b in boxes[i + 1:]:
            assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (ka, kb)
    p = rb["pieces_mm"]
    for blk, arms in v31.BLOCKS.items():
        pos = [p[f"{blk}:{a}"][1 if v31.ORIENT.get(blk) == "v" else 0] for a in arms]
        assert pos == sorted(pos) and len(set(pos)) == len(pos), (blk, pos)
    # no two arms closer than 2 mm, so the decoded file's owner rule is unambiguous
    keys = sorted(p)
    for i, ka in enumerate(keys):
        for kb in keys[i + 1:]:
            a, b = p[ka], p[kb]
            gapx = max(a[0] - b[2], b[0] - a[2])
            gapy = max(a[1] - b[3], b[1] - a[3])
            assert max(gapx, gapy) >= 2.0, (ka, kb)


def test_every_arm_differs_from_the_first_in_its_block(card):
    _out, rb = card
    n = rb["stitches_by_piece"]
    assert n["T:today"] != n["T:wordtier"]
    assert n["N:keep-off"] != n["N:keep-on"]
    assert n["G:gap-off"] != n["G:gap-0.8"]
    assert n["F3:today"] != n["F3:floor"] or n["F3:today"] != n["F3:keep"]
    assert n["S:today"] != n["S:floor-1.0"] and n["S:today"] != n["S:floor-0.73"]
    assert n["S:floor-1.0"] != n["S:floor-0.73"]
    assert n["E2:today"] != n["E2:floor-0.73"]
    assert n["X:ends-off"] != n["X:ends-on"]
    assert n["B:ends-off"] != n["B:ends-on"]
    # the tier sews fewer stitches than the outline it replaces (#913)
    assert n["S:floor-0.73"] < n["S:today"] and n["E2:floor-0.73"] < n["E2:today"]
    pieces = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    assert pieces[("S", "floor-0.73")]["overrides"]["small_lettering_skeleton_floor_mm"] == 0.73
    assert pieces[("X", "ends-on")]["overrides"]["lettering_columns_square_ends"] is True
    assert pieces[("B", "ends-off")]["overrides"]["lettering_columns_inside_connectors"] is False
    assert pieces[("B", "ends-off")]["garment_id"] == "left_chest"


def test_the_index_strips_and_labels_hold_the_one_millimetre_floor(card):
    _out, rb = card
    assert not [k for k in rb["under_1mm_by_piece"] if k.endswith(":strips")], rb["under_1mm_by_piece"]


def test_the_earlier_cards_are_kept_and_not_overwritten(card):
    """v3.1 writes beside v1, v2 and v3, never over them."""
    assert COMMITTED.name == "card-v3-2026-10-13"
    assert (COMMITTED.parent / "hairline-card-2026-10-12" / "hairline_card_40wt.dst").exists()
    assert (COMMITTED.parent / "card-v2-2026-10-13" / "card_v2_40wt.dst").exists()
    for name in ("card_v3_40wt.dst", "card_v3_40wt.png", "card_v3_40wt_blocks.png", "README-v3.md",
                 "scoring-sheet-v3.md", "readback-v3.json", "readback-v3.md"):
        assert (COMMITTED / name).exists(), name
    out, _rb = card
    assert (out / "card_v3_1_40wt.dst").exists() and not (out / "card_v3_40wt.dst").exists()


def test_the_readout_sheet_names_every_block_and_arm():
    sheet = (COMMITTED / "scoring-sheet.md").read_text(encoding="utf-8")
    for needle in ("## F3", "## T", "## N", "## G", "## X", "## S", "## B", "## E2",
                   "small_print_floor", "small_glyph_keep", "lettering_words", "lettering_word_tiers",
                   "forbid_gap_mm", "small_lettering_skeleton", "small_lettering_skeleton_floor_mm",
                   "lettering_columns_square_ends", "lettering_columns_inside_connectors",
                   "R of PRISES", "1 tooth", "2 teeth", "3 teeth"):
        assert needle in sheet, needle


def test_the_readme_says_what_the_card_pins_and_drops():
    text = (COMMITTED / "README.md").read_text(encoding="utf-8")
    for needle in ("small_text_cap_mm", "#909", "small_text_restore_mm", "#911", "#913",
                   "verification", "4 x 4 in", "card_v3_1_40wt.dst", "No skeleton arm"):
        assert needle in text, needle
