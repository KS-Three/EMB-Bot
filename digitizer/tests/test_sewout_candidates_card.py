"""The sew-out card v2 (`tools/sewout_candidates_card.py`, 2026-10-13).

Every open stitch candidate on one card, each an OFF vs ON pair: F small-print
counters (`cfg.small_print_floor`), G forbid gap (`cfg.forbid_gap_mm`), H
column reach (`cfg.lettering_columns`). These tests regenerate the card in a
temp dir and check the FILES against the committed read-back
(`docs/sewout/card-v2-2026-10-13/readback.json`); the cloth is Kent's to judge
(ROADMAP gate 1), and no engine code is touched.

Counts that cannot move (blocks, colours, colour changes, pieces) are compared
exactly. Lengths, extents and stitch counts come out of the digitizer, whose
numerics differ a little per platform (the golden-hash tests are why), so they
are compared within a tolerance: 0.5 mm on a size, 3% on a count.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pystitch
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools import sewout_candidates_card as v2  # noqa: E402

COMMITTED = v2.REPO / "docs" / "sewout" / "card-v2-2026-10-13"


@pytest.fixture(scope="module")
def card(tmp_path_factory):
    out = tmp_path_factory.mktemp("cardv2")
    table = v2.generate(out, None, quiet=True)
    return out, table


@pytest.fixture(scope="module")
def committed():
    return json.loads((COMMITTED / "readback.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize("wt", ["40wt", "60wt"])
def test_regenerated_readback_matches_the_committed_one(card, committed, wt):
    """The done-test: block count, colour count, longest stitch, extents."""
    _out, table = card
    new, old = table[wt], committed[wt]
    assert new["blocks"] == old["blocks"] == 3
    assert new["colours"] == old["colours"] == 3
    assert new["colour_changes_file"] == new["colour_changes_plan"] == old["colour_changes_file"] == 2
    assert [s["thread"] for s in new["stops"]] == [s["thread"] for s in old["stops"]] == ["dark", "light", "dark"]
    assert new["max_needle_stitch_mm"] == pytest.approx(old["max_needle_stitch_mm"], abs=0.5)
    assert new["max_record_axis_mm"] == pytest.approx(old["max_record_axis_mm"], abs=0.2)
    for key in ("extent_mm", "x_range_mm", "y_range_mm"):
        assert new[key] == pytest.approx(old[key], abs=0.5), key
    assert new["stitches_file"] == pytest.approx(old["stitches_file"], rel=0.03)
    assert sorted(new["blocks_mm"]) == sorted(old["blocks_mm"]) == ["F", "G", "H"]
    assert sorted(new["pieces_mm"]) == sorted(old["pieces_mm"])


@pytest.mark.parametrize("wt", ["40wt", "60wt"])
def test_each_hoop_fits_and_reads_back_whole(card, wt):
    out, table = card
    rb = table[wt]
    assert rb["within_hoop"] and max(rb["extent_mm"]) <= v2.HOOP_MM
    # Not larger than card v1's 94 x 82 mm design in either direction.
    assert rb["extent_mm"][0] <= 96.0 and rb["extent_mm"][1] <= 82.0
    assert rb["stitches_file"] == rb["stitches_plan"] > 1000
    assert rb["colour_changes_file"] == rb["colour_changes_plan"]
    # No stitch over the format's 12.1 mm, by needle stitch and by record.
    assert rb["max_needle_stitch_mm"] <= v2.MAX_RECORD_MM
    assert rb["max_record_axis_mm"] <= v2.MAX_RECORD_MM + 1e-6
    # The file on disk is the one the read-back describes.
    pat = pystitch.read_dst(str(out / rb["file"]))
    n = sum(1 for _x, _y, cmd in pat.stitches if (cmd & pystitch.COMMAND_MASK) == pystitch.STITCH)
    assert n == rb["stitches_file"]


def test_every_pair_is_there_and_the_blocks_do_not_overlap(card):
    _out, table = card
    for rb in table.values():
        assert set(rb["pieces_mm"]) == {
            "F:4.0-off", "F:4.0-on", "F:3.0-off", "F:3.0-on",
            "G:gap-off", "G:gap-0.4", "G:gap-0.8", "H:reach-off", "H:reach-on"}
        boxes = sorted(rb["blocks_mm"].items())
        for k, (x0, y0, x1, y1) in boxes:
            assert -50 <= x0 < x1 <= 50 and -50 <= y0 < y1 <= 50, k
        for i, (ka, a) in enumerate(boxes):
            for kb, b in boxes[i + 1:]:
                assert a[2] <= b[0] or b[2] <= a[0] or a[3] <= b[1] or b[3] <= a[1], (ka, kb)
        # An OFF piece sits left of (F, G) or above (H) its ON partner, as labelled.
        p = rb["pieces_mm"]
        assert p["F:4.0-off"][0] < p["F:4.0-on"][0] < p["F:3.0-off"][0] < p["F:3.0-on"][0]
        assert p["G:gap-off"][0] < p["G:gap-0.4"][0] < p["G:gap-0.8"][0]
        assert p["H:reach-off"][1] < p["H:reach-on"][1]


def test_on_differs_from_off_in_every_pair(card):
    """An ON arm that is the OFF arm would make the pair a blank test."""
    _out, table = card
    for wt, rb in table.items():
        n = rb["stitches_by_piece"]
        assert n["F:4.0-off"] != n["F:4.0-on"] or n["F:3.0-off"] != n["F:3.0-on"], wt
        assert n["G:gap-off"] != n["G:gap-0.8"], wt
        assert n["H:reach-off"] != n["H:reach-on"], wt
        pieces = {p["arm"]: p for p in rb["pieces"]}
        assert pieces["4.0-on"]["small_print_floor"] and not pieces["4.0-off"]["small_print_floor"]
        assert pieces["gap-off"]["forbid_gap_mm"] is None and pieces["gap-0.8"]["forbid_gap_mm"] == 0.8
        assert pieces["reach-on"]["lettering_columns"] and not pieces["reach-off"]["lettering_columns"]


def test_the_index_strips_and_labels_hold_the_one_millimetre_floor(card):
    """Under 1.0 mm only in the digitizer's own pieces (F, G, H arms), never in
    the strips or labels the card adds."""
    _out, table = card
    for rb in table.values():
        assert not [k for k in rb["under_1mm_by_piece"] if k.endswith(":strips")], rb["under_1mm_by_piece"]


def test_the_hairline_card_is_not_overwritten(card):
    """v2 writes beside v1, never over it."""
    assert COMMITTED.name == "card-v2-2026-10-13"
    assert (COMMITTED.parent / "hairline-card-2026-10-12" / "hairline_card_40wt.dst").exists()
