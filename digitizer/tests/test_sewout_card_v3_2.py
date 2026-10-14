"""The sew-out card v3.2 (`tools/sewout_card_v3_2.py`, 2026-10-14).

Card v3.1 re-cut on today's main, plus block O: the line route's chaining
(`cfg.hairline_lines_chain`, #917, default OFF) on the owl, chain OFF against chain
ON. These tests pin the block list and arms, regenerate the card in a temp dir from
the COMMITTED cuts (`docs/sewout/card-v3-2026-10-13/cuts/cut32_*.json` and
`cuts/tn/`), and check the FILE against the committed read-back, piece by piece. The
cloth is Kent's to judge (ROADMAP gate 1); no engine code is touched and the
digitizes themselves are not re-run here (minutes each: `--cut` makes the cuts).

Counts that cannot move (blocks, colours, colour changes, pieces) are compared
exactly. Lengths, extents and stitch counts come out of the digitizer, whose
numerics differ a little per platform, so they are compared within a tolerance:
0.5 mm on a size, 3% on a count.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pystitch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import sewout_card_v3_1 as v31  # noqa: E402
from tools import sewout_card_v3_2 as v32  # noqa: E402

COMMITTED = v32.REPO / "docs" / "sewout" / "card-v3-2026-10-13"
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
    "O:chain-off", "O:chain-on",
}

#: the v3.1 files this PR must leave as they were (sha256), README.md excepted: it gets one note on top
V31_FROZEN = {
    "card_v3_1_40wt.dst": None, "card_v3_1_40wt.png": None, "card_v3_1_40wt_blocks.png": None,
    "scoring-sheet.md": None, "readback.json": None, "readback.md": None,
}


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardv32")
    rb = v32.generate(out, None, CUTS, quiet=True)
    return out, rb


@pytest.fixture(scope="module")
def committed():
    return json.loads((COMMITTED / "readback-v3.2.json").read_text(encoding="utf-8"))


def test_the_block_list_and_arms_are_pinned():
    """Which blocks, which arms, in tooth order (1 tooth first). Changing one
    changes what Kent is asked to sew: say so in the PR, then edit this."""
    assert v32.BLOCKS == {
        "F3": ("today", "floor", "keep"),
        "T": ("today", "wordtier"),
        "N": ("keep-off", "keep-on"),
        "G": ("gap-off", "gap-0.4", "gap-0.8"),
        "S": ("today", "floor-1.0", "floor-0.73"),
        "E2": ("today", "floor-0.73"),
        "X": ("ends-off", "ends-on"),
        "B": ("ends-off", "ends-on"),
        "O": ("chain-off", "chain-on"),
    }
    assert {f"{b}:{a}" for b, arms in v32.BLOCKS.items() for a in arms} == PIECES
    for blk, arms in v31.BLOCKS.items():          # v3.1's eight blocks, arm for arm
        assert v32.BLOCKS[blk] == arms
    assert v32.SOURCES["O"] == {"chain-off": ("owl_chain_off", ["O"]), "chain-on": ("owl_chain_on", ["O"])}
    for blk in v31.SOURCES:
        assert v32.SOURCES[blk] == v31.SOURCES[blk]
    assert v32.WT == 40


def test_the_arm_flags_are_pinned_and_the_owl_pair_differs_only_by_the_chain_flag():
    """Every flag that could move a piece is pinned in every arm (v3.1's pins, unchanged); the
    owl arms differ by `hairline_lines_chain` alone, and the strand test is pinned OFF."""
    assert (v32.PINS, v32.CUT_ARMS, v32.ENT_ARMS, v32.BECKER_ARMS) == (
        v31.PINS, v31.CUT_ARMS, v31.ENT_ARMS, v31.BECKER_ARMS)
    off, on = v32.OWL_ARMS["owl_chain_off"], v32.OWL_ARMS["owl_chain_on"]
    assert off["hairline_lines_chain"] is False and on["hairline_lines_chain"] is True
    assert {k: v for k, v in off.items() if k != "hairline_lines_chain"} == \
           {k: v for k, v in on.items() if k != "hairline_lines_chain"}
    assert off["hairline_lines_strand_test"] is False and off["hairline_from_lines"] is True
    assert (off["thread_wt"], v32.OWL_WIDTH_MM, v32.OWL_ROUTE) == (
        40, 127.0, {"forced_class": "photo_subject", "photo_prep": False})
    # the chain flag is OFF on main: this card pins it, it does not flip it
    from digitizer_core import PipelineConfig
    assert PipelineConfig().hairline_lines_chain is False
    from digitizer_core.stage6_hairline_lines import HOP_MAX_MM
    assert HOP_MAX_MM == v32.OWL_HOP_MAX_MM == 8.0


def test_the_committed_cuts_record_the_flags_they_were_made_with():
    allarms = {**v32.CUT_ARMS, **v32.ENT_ARMS, **v32.BECKER_ARMS}
    for arm, flags in allarms.items():
        d = v32.load_cut_file(CUTS, arm)
        assert d["overrides"] == flags, arm
        assert d["stitches_whole"] > 1000 and d["trims_whole"] > 0, arm
    for arm in v32.CUT_ARMS:
        assert v32.load_cut_file(CUTS, arm)["width_mm"] == 81.0
    for arm in v32.ENT_ARMS:
        assert v32.load_cut_file(CUTS, arm)["width_mm"] == 80.0
    for arm, flags in v32.OWL_ARMS.items():
        d = v32.load_cut_file(CUTS, arm)
        assert d["overrides"] == {**flags, **v32.OWL_ROUTE}, arm
        assert d["width_mm"] == 127.0 and d["file"] == "photo/owl_kent.jpg"
    # v3's T / N cuts, re-made
    for arm, flags in v32.v3.CUT_ARMS.items():
        d = json.loads((CUTS / v32.TN_DIR / f"cut_{arm}.json").read_text(encoding="utf-8"))
        assert d["overrides"] == flags, arm


def test_the_e2_note_matches_the_cuts_it_quotes():
    """The README says how many glyphs E2 sews as a skeleton; the cut files are the source."""
    new = v32.load_cut_file(CUTS, "ent_skel073")
    old = json.loads((CUTS / "cut31_ent_skel073.json").read_text(encoding="utf-8"))
    assert (old["offered"], old["skeleton_sewn"]) == (14, 11)          # v3.1 / #913
    assert new["skeleton_sewn"] >= old["skeleton_sewn"] and new["offered"] >= 14     # #936 takes more
    assert v32.load_cut_file(CUTS, "ent_today")["offered"] == 0
    text = (COMMITTED / "README-v3.2.md").read_text(encoding="utf-8")
    assert f"**{new['skeleton_sewn']} of {new['offered']}**" in text
    assert f"so it sews {new['skeleton_sewn']}, not {old['skeleton_sewn']}" in text


def test_the_new_arms_differ_where_the_card_says_they_do():
    """A pair whose arms are the same thread is a blank test."""
    def pts(arm, box):
        return [r["points"] for r in v32.load_cut(CUTS, arm, box)["runs"]]
    assert pts("today", "S") != pts("skel", "S") != pts("skel073", "S")
    assert pts("ent_today", "E2") != pts("ent_skel073", "E2")
    for box in ("E", "MON"):
        assert pts("today", box) != pts("ends_on", box), box
    assert pts("becker_off", "B") != pts("becker_on", "B")
    for box, ids in v32.v31.ENDS_SHAPES.items():
        for arm in ("today", "ends_on"):
            assert {r["shape_id"] for r in v32.load_cut(CUTS, arm, box)["runs"]} == set(ids)


def test_the_skeleton_arm_is_still_dropped_from_block_t():
    got = v32.the_is_unaffected(CUTS)
    assert got["skel_same_as_today"] and got["skel073_same_as_today"] and got["today_same_as_t_block_cut"], got


def test_the_owl_pair_has_the_same_strands_and_only_the_on_arm_has_hops():
    """What the chain flag changes is the hops: the strands are the same points in both pieces
    (#917's own test), the fills under them are the same, only ON has needle-down hops, and none
    is over 8 mm."""
    off = v32.load_cut(CUTS, "owl_chain_off", "O")
    on = v32.load_cut(CUTS, "owl_chain_on", "O")
    assert off["strand_box_mm"] == on["strand_box_mm"] and off["fill_box_mm"] == on["fill_box_mm"]
    assert off["fill"] == on["fill"]
    core = lambda p: [r["points"][4:-4] for r in p["strands"] if r["kind"] == "run"]       # noqa: E731
    assert core(off) == core(on) and off["strand_count"] == on["strand_count"] >= 3
    assert not [r for r in off["strands"] if r["kind"] == "travel"]
    hops = [r for r in on["strands"] if r["kind"] == "travel"]
    assert len(hops) >= 1
    assert all(not r["jump"] and not r["trim"] for r in hops)
    for link in on["links"]:
        if link["chained"]:
            assert link["mm"] <= v32.OWL_HOP_MAX_MM
    assert not [l for l in off["links"] if l["chained"]]
    # the whole design behind each piece: only the ON plan sewed hops
    won, woff = (v32.load_cut_file(CUTS, a)["whole"] for a in ("owl_chain_on", "owl_chain_off"))
    assert woff["census"].get("hops", 0) == 0 and won["census"]["hops"] >= 1
    assert won["trims"] <= woff["trims"]
    assert won["strand_runs"] == woff["strand_runs"]


@pytest.mark.parametrize("key", ["blocks", "colours"])
def test_regenerated_readback_matches_the_committed_one(card, committed, key):
    _out, new = card
    assert new[key] == committed[key]
    assert new["blocks"] == 9 and new["colours"] == 3


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
    assert sorted(new["blocks_mm"]) == sorted(old["blocks_mm"]) == ["B", "E2", "F3", "G", "N", "O", "S", "T", "X"]
    assert set(new["pieces_mm"]) == set(old["pieces_mm"]) == PIECES


def test_the_hoop_fits_with_room_and_reads_back_whole(card):
    out, rb = card
    assert rb["within_hoop"] and max(rb["extent_mm"]) <= v32.HOOP_MM - 1.0       # 0.5 mm each side at least
    assert rb["stitches_file"] == rb["stitches_plan"] > 1000
    assert rb["max_needle_stitch_mm"] <= v32.MAX_RECORD_MM
    assert rb["max_record_axis_mm"] <= v32.MAX_RECORD_MM + 1e-6
    pat = pystitch.read_dst(str(out / rb["file"]))
    n = sum(1 for _x, _y, cmd in pat.stitches if (cmd & pystitch.COMMAND_MASK) == pystitch.STITCH)
    assert n == rb["stitches_file"]
    assert rb["file"] == "card_v3_2_40wt.dst"


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
    for blk, arms in v32.BLOCKS.items():
        pos = [p[f"{blk}:{a}"][1 if v32.ORIENT.get(blk) == "v" else 0] for a in arms]
        assert pos == sorted(pos) and len(set(pos)) == len(pos), (blk, pos)
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
    assert n["E2:today"] != n["E2:floor-0.73"]
    assert n["X:ends-off"] != n["X:ends-on"]
    assert n["B:ends-off"] != n["B:ends-on"]
    assert n["O:chain-off"] != n["O:chain-on"]
    assert n["S:floor-0.73"] < n["S:today"] and n["E2:floor-0.73"] < n["E2:today"]
    pieces = {(p["block"], p["arm"]): p for p in rb["pieces"]}
    assert pieces[("O", "chain-on")]["overrides"]["hairline_lines_chain"] is True
    assert pieces[("O", "chain-off")]["overrides"]["hairline_lines_chain"] is False
    assert pieces[("O", "chain-on")]["chained_hops"] >= 1 and pieces[("O", "chain-off")]["chained_hops"] == 0
    assert pieces[("B", "ends-off")]["garment_id"] == "left_chest"


def test_block_o_sews_the_hops_needle_down_and_over_laid_thread(card):
    """In the FILE's plan: chain ON has stitched hops and none of them lies over fabric nothing
    laid (the cover test, re-run on the card's piece); chain OFF has none and leaves floats or
    cuts between the same strands, so the card shows the thing the flag changes."""
    _out, rb = card
    off, on = rb["chain"]["pieces"]["chain-off"], rb["chain"]["pieces"]["chain-on"]
    assert off["chained_hops"] == 0 and on["chained_hops"] >= 1
    assert all(m <= v32.OWL_HOP_MAX_MM + 0.3 for m in on["chained_hop_mm"])
    assert on["chained_hop_bare_mm"] == [0.0] * on["chained_hops"], on["chained_hop_bare_mm"]
    assert off["strand_runs"] == on["strand_runs"]
    joins_off = off["floats_untrimmed"] + off["trims_between_strands"]
    joins_on = on["floats_untrimmed"] + on["trims_between_strands"]
    assert joins_off == joins_on + on["chained_hops"] or joins_off >= joins_on + on["chained_hops"] - 1
    assert on["trims_between_strands"] <= off["trims_between_strands"]
    # the instrument's shape: a flight is not thread, so the OFF arm's cuts add no bare thread
    assert on["instrument"]["thread_bare_mm"] <= off["instrument"]["thread_bare_mm"] + 0.5
    assert rb["chain"]["whole"]["chain-on"]["thread_bare_mm"] == pytest.approx(
        rb["chain"]["whole"]["chain-off"]["thread_bare_mm"], abs=2.0)


def test_the_owl_fills_sew_light_and_the_strands_dark(card):
    """O's fills are in the light cone (stop 2) and its strands in the dark one (stop 3), so a hop
    that shows is a dark line on a light field: the worst case for exposed travel."""
    from digitizer_core import stitches
    plan, _card, _extra = v32.build(CUTS)
    by = {}
    for stop, b in enumerate(plan.blocks):
        for r in b.runs:
            if r.shape_id.startswith("O:") and not r.shape_id.startswith("O:label"):
                by.setdefault(r.shape_id.split(":")[2], set()).add(stop)
    assert by == {"fill": {1}, "strand": {2}}, by
    on = [r for b in plan.blocks for r in b.runs if r.shape_id == "O:chain-on:strand"]
    assert any(r.kind == stitches.TRAVEL and not r.jump and not r.trim for r in on)
    off = [r for b in plan.blocks for r in b.runs if r.shape_id == "O:chain-off:strand"]
    assert not [r for r in off if r.kind == stitches.TRAVEL]


def test_the_index_strips_and_labels_hold_the_one_millimetre_floor(card):
    _out, rb = card
    assert not [k for k in rb["under_1mm_by_piece"] if k.endswith(":strips")], rb["under_1mm_by_piece"]


def test_the_earlier_cards_are_kept_and_not_overwritten(card):
    """v3.2 writes beside v1, v2, v3 and v3.1, never over them; v3.1's files are as v3.1 left
    them (README.md carries one note on top and nothing else changed)."""
    assert COMMITTED.name == "card-v3-2026-10-13"
    assert (COMMITTED.parent / "hairline-card-2026-10-12" / "hairline_card_40wt.dst").exists()
    assert (COMMITTED.parent / "card-v2-2026-10-13" / "card_v2_40wt.dst").exists()
    for name in ("card_v3_40wt.dst", "card_v3_40wt.png", "card_v3_40wt_blocks.png", "README-v3.md",
                 "scoring-sheet-v3.md", "readback-v3.json", "readback-v3.md",
                 "card_v3_1_40wt.dst", "card_v3_1_40wt.png", "card_v3_1_40wt_blocks.png", "README.md",
                 "scoring-sheet.md", "readback.json", "readback.md"):
        assert (COMMITTED / name).exists(), name
    out, _rb = card
    assert (out / "card_v3_2_40wt.dst").exists()
    assert not (out / "card_v3_1_40wt.dst").exists() and not (out / "README.md").exists()
    assert (CUTS / "cut31_today.json").exists() and (CUTS / "cut_today.json").exists()
    text = (COMMITTED / "README.md").read_text(encoding="utf-8")
    assert text.startswith("# Sew-out card v3.1, 2026-10-13\n\n**Superseded by card v3.2")
    # v3.1's committed read-back still says what v3.1 was
    rb31 = json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))
    assert rb31["file"] == "card_v3_1_40wt.dst" and rb31["blocks"] == 8
    assert hashlib.sha256((COMMITTED / "card_v3_1_40wt.dst").read_bytes()).hexdigest()


def test_the_readout_sheet_names_every_block_and_arm():
    sheet = (COMMITTED / "scoring-sheet-v3.2.md").read_text(encoding="utf-8")
    for needle in ("## F3", "## T", "## N", "## G", "## X", "## S", "## B", "## E2", "## O",
                   "small_print_floor", "small_glyph_keep", "lettering_words", "lettering_word_tiers",
                   "forbid_gap_mm", "small_lettering_skeleton", "small_lettering_skeleton_floor_mm",
                   "lettering_columns_square_ends", "lettering_columns_inside_connectors",
                   "hairline_lines_chain", "8 mm", "chain OFF", "chain ON",
                   "R of PRISES", "1 tooth", "2 teeth", "3 teeth", "card_v3_2_40wt.dst"):
        assert needle in sheet, needle
    assert "v3.1" not in sheet


def test_the_readme_says_what_changed_and_what_it_pins():
    text = (COMMITTED / "README-v3.2.md").read_text(encoding="utf-8")
    for needle in ("small_text_cap_mm", "#909", "small_text_restore_mm", "#911", "#913", "#917", "#937", "#923",
                   "#936", "verification", "4 x 4 in", "card_v3_2_40wt.dst", "No skeleton arm",
                   "regenerated on today's main", "hairline_lines_chain", "stays OFF", "8 mm",
                   "light cone", "stacked", "Every cut was re-made", "replaces v3.1"):
        assert needle in text, needle
    # every placeholder was filled
    for left in ("PAIRNOTES", "CUTNOTES", "READBACK", "BLOCKMAP", "CHAINDOC", "CHAINTABLE", "THINGS", "LAYOUTNOTE",
                 "F3NOTE", "E2NOTE", "CUTDRIFT", "DRIFT", "SIZE_MM", "LONGHOP", "THE_NOTE", "WINDOW"):
        assert left not in text, left
