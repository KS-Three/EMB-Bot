"""`tools/lettering_board.py` -- one board delta for every lettering PR.

The pure layer (bands, pooling, n/a, compare, render, the pinned lines) runs
anywhere. The reader tests draw a two-letter satin word as a DST and read it
back through the same path the board reads the pro's file. The smoke test
digitizes one small committed pair (Becker's chest logo, `testdata/reference`)
end to end and checks the board's shape and that every n/a carries a reason.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import lettering_board as lb  # noqa: E402

DIGITIZER = HERE.parent


# --- size bands --------------------------------------------------------------

@pytest.mark.parametrize("h,band", [
    (0.5, "<4"), (3.99, "<4"), (4.0, "4-6"), (5.99, "4-6"), (6.0, "6-10"),
    (9.99, "6-10"), (10.0, "10+"), (28.5, "10+"),
])
def test_band_edges(h, band):
    assert lb.band_of(h) == band


def test_band_of_nothing_is_none_not_the_first_band():
    assert lb.band_of(None) is None


# --- slots and pooling -------------------------------------------------------

def line(slug, text, band="4-6", **sides):
    return {"slug": slug, "text": text, "band": band, "art_h": 4.0,
            "ours": sides.get("ours", {}), "pro": sides.get("pro", {})}


def slot(v, w=None, why=None):
    return lb.slot(v, w=w, why=why)


def test_a_missing_value_keeps_its_reason_and_is_never_zero():
    s = lb.slot(None, why="no DST sibling")
    assert s["v"] is None and s["why"] == "no DST sibling"
    assert lb.slot(0)["v"] == 0 and lb.slot(0)["why"] is None     # a real zero is a zero


def test_sum_cell_counts_only_lines_both_sides_have_and_says_how_many():
    lines = [
        line("a", "X", ours={"columns": slot(10)}, pro={"columns": slot(8)}),
        line("a", "Y", ours={"columns": slot(4)}, pro={"columns": slot(None, why="pro DROPPED")}),
        line("a", "Z", ours={"columns": slot(6)}, pro={"columns": slot(5)}),
    ]
    got = lb.pool(lines, "columns")
    assert (got["ours"], got["pro"]) == (16, 13)       # Y is left out of BOTH sides
    assert (got["n"], got["of"]) == (2, 3)
    assert got["why"] is None


def test_cell_with_no_usable_line_is_n_a_with_the_commonest_reason():
    lines = [
        line("a", "X", ours={"trims": slot(3)}, pro={"trims": slot(None, why="PES has no trim records")}),
        line("a", "Y", ours={"trims": slot(2)}, pro={"trims": slot(None, why="PES has no trim records")}),
    ]
    got = lb.pool(lines, "trims")
    assert got["ours"] is None and got["pro"] is None
    assert got["why"] == "PES has no trim records"
    assert (got["n"], got["of"]) == (0, 2)


def test_mean_cell_is_weighted_by_its_own_weight_not_by_line():
    lines = [
        line("a", "X", ours={"satin_w": slot(1.0, w=10)}, pro={"satin_w": slot(1.2, w=10)}),
        line("a", "Y", ours={"satin_w": slot(2.0, w=30)}, pro={"satin_w": slot(2.0, w=30)}),
    ]
    got = lb.pool(lines, "satin_w")
    assert got["ours"] == pytest.approx((1.0 * 10 + 2.0 * 30) / 40)
    assert got["pro"] == pytest.approx((1.2 * 10 + 2.0 * 30) / 40)


def test_a_weightless_mean_line_is_not_a_zero_width():
    lines = [line("a", "X", ours={"satin_w": slot(None, why="no satin crosses")},
                  pro={"satin_w": slot(1.1, w=12)})]
    got = lb.pool(lines, "satin_w")
    assert got["ours"] is None and got["why"] == "no satin crosses"


# --- the board ---------------------------------------------------------------

def sample_lines():
    return [
        line("fremont_hat", "EST", band="<4",
             ours={"columns": slot(0), "stitches": slot(120), "trims": slot(2), "satin_w": slot(None, why="no satin crosses"),
                   "cc": slot(0.0, w=3)},
             pro={"columns": slot(7), "stitches": slot(200), "trims": slot(1), "satin_w": slot(1.0, w=40),
                  "cc": slot(1.0, w=3)}),
        line("fremont_hat", "THE", band="<4",
             ours={"columns": slot(1), "stitches": slot(100), "trims": slot(0), "satin_w": slot(0.7, w=10),
                   "cc": slot(None, why="not located in ours")},
             pro={"columns": slot(6), "stitches": slot(180), "trims": slot(0), "satin_w": slot(1.1, w=30),
                  "cc": slot(None, why="not located in ours")}),
        line("becker_hat_small", "MARINE", band="10+",
             ours={"columns": slot(22), "stitches": slot(900), "trims": slot(5), "satin_w": slot(1.4, w=200),
                   "cc": slot(1.0, w=6)},
             pro={"columns": slot(20), "stitches": slot(850), "trims": slot(3), "satin_w": slot(1.5, w=210),
                  "cc": slot(1.0, w=6)}),
    ]


def test_cells_group_by_pair_and_band_and_total_every_band():
    cells = lb.cells(sample_lines())
    assert set(cells) == {"fremont_hat", "becker_hat_small", "ALL"}
    assert cells["fremont_hat"]["<4"]["columns"]["ours"] == 1
    assert cells["fremont_hat"]["<4"]["columns"]["pro"] == 13
    assert cells["ALL"]["10+"]["stitches"]["ours"] == 900
    assert cells["ALL"]["<4"]["cc"]["n"] == 1         # THE's cc is n/a, EST's is the only one


def test_markdown_prints_n_a_for_a_missing_cell_and_says_why():
    lines = [line("fremont_hat", "EST", band="<4",
                  ours={"satin_w": slot(None, why="no satin crosses"), "columns": slot(0)},
                  pro={"satin_w": slot(1.0, w=40), "columns": slot(7)})]
    md = lb.render_md({"meta": {"date": "2026-10-25", "sets": {}, "git": "abc1234", "tesseract": None},
                       "lines": lines, "cells": lb.cells(lines)})
    row = next(r for r in md.splitlines() if r.startswith("| fremont_hat | <4"))
    cols = [c.strip() for c in row.strip("|").split("|")]
    head = next(r for r in md.splitlines() if r.startswith("| pair | band"))
    heads = [c.strip() for c in head.strip("|").split("|")]
    assert cols[heads.index("mean satin width mm")] == "n/a"        # not "0.00 / 1.00"
    assert cols[heads.index("columns")] == "0 / 7"                   # a real zero stays one
    assert "no satin crosses" in md                                  # and the reason is printed


def test_markdown_lists_every_line_and_the_pairs_it_skipped():
    lines = sample_lines()
    board = board_of(lines)
    board["meta"]["skipped"] = [{"slug": "tires_hat_3d", "why": "no lettering lines pinned"}]
    md = lb.render_md(board)
    assert "tires_hat_3d: no lettering lines pinned" in md
    for ln in lines:
        assert f"| {ln['slug']} | {ln['text']} |" in md


# --- compare -----------------------------------------------------------------

def board_of(lines, **meta):
    return {"meta": {"date": "2026-10-25", "sets": {}, "git": "x", **meta}, "lines": lines,
            "cells": lb.cells(lines)}


def table_rows(md):
    return [[c.strip() for c in r.strip("|").split("|")] for r in md.splitlines()
            if r.startswith("|") and not r.startswith("|---") and not r.startswith("| pair")]


def test_compare_prints_the_delta_on_lines_both_runs_have():
    a, b = sample_lines(), sample_lines()
    b[0]["ours"]["columns"] = slot(5)         # EST 0 -> 5, THE stays 1: the cell goes 1 -> 6
    b[0]["ours"]["trims"] = slot(1)           # 2 -> 1
    rows = table_rows(lb.compare_boards(board_of(a), board_of(b, sets={"x": True})))
    cols = next(r for r in rows if r[:3] == ["fremont_hat", "<4", "columns"])
    assert cols[3:5] == ["1 -> 6", "+5"] and cols[5] == "13"          # the pro's 7 + 6, unmoved
    trims = next(r for r in rows if r[:3] == ["fremont_hat", "<4", "trims inside letters"])
    assert trims[3:5] == ["2 -> 1", "-1"]
    assert not any(r[0] == "becker_hat_small" for r in rows if r[2] == "columns")   # unmoved pair: not listed


def test_compare_lists_a_line_one_run_lost_instead_of_calling_it_a_change():
    a, b = sample_lines(), sample_lines()
    b[2]["ours"]["columns"] = slot(None, why="ours DROPPED")
    md = lb.compare_boards(board_of(a), board_of(b))
    assert "lost: becker_hat_small / MARINE, columns: B reads n/a (ours DROPPED)" in md
    rows = table_rows(md)
    # MARINE is the only 10+ line, so no 10+ columns delta exists to report
    assert not [r for r in rows if r[1] == "10+" and r[2] == "columns"]


def test_compare_of_a_board_with_itself_changes_nothing():
    a = board_of(sample_lines())
    md = lb.compare_boards(a, a)
    assert "No change in any cell." in md
    assert not any(r[0] != "ALL" for r in table_rows(md))


def test_compare_names_lines_that_joined_or_left():
    a, b = sample_lines(), sample_lines()[:2]
    md = lb.compare_boards(board_of(a), board_of(b))
    assert "gone: becker_hat_small / MARINE" in md


# --- the pinned lines --------------------------------------------------------

def test_every_pinned_line_is_well_formed_and_on_a_known_pair():
    reg = lb.load_lines()
    known = {r[0] for r in lb.pair_rows()}
    assert reg, "no lines pinned"
    for slug, spec in reg.items():
        assert slug in known, f"{slug}: not in border_census.PAIRS or its extras"
        assert spec["lines"], slug
        seen = set()
        for ln in spec["lines"]:
            assert ln["text"] and ln["text"] not in seen, (slug, ln)
            seen.add(ln["text"])
            x0, y0, x1, y1 = ln["box"]
            assert x1 > x0 and y1 > y0, (slug, ln)
            assert ln["art_h"] > 0.3, (slug, ln)
            for w in ln.get("words", []):
                assert isinstance(w, str)


def test_a_pair_left_off_the_board_says_why_and_is_not_also_on_it():
    known = {r[0] for r in lb.pair_rows()}
    left = lb.load_left_off()
    assert left, "nothing is left off: drop this test or the list"
    for slug, why in left.items():
        assert slug in known and slug not in lb.load_lines(), slug
        assert len(why) > 40, f"{slug}: a reason, not a label"


def test_pinned_words_exist_in_the_legibility_words_file():
    from tools import word_legibility as wl
    for slug, spec in lb.load_lines().items():
        job = spec.get("legibility_job")
        if not job:
            continue
        have = {w["text"] for w in wl.pinned_words(job)}
        for ln in spec["lines"]:
            for w in ln.get("words", []):
                assert w in have, f"{slug}/{ln['text']}: word {w!r} is not pinned for {job}"


def test_the_committed_pairs_cover_every_band():
    """The board is only a board if each size band has something in it."""
    got = {ln_band for ln_band in (lb.band_of(ln["art_h"]) for spec in lb.load_lines().values()
                                   for ln in spec["lines"])}
    assert got == {"<4", "4-6", "6-10", "10+"}


# --- the reader, on a word drawn as satin -----------------------------------------

def _column(x0, y0, h=3.0, w=1.2, pitch=0.4):
    """One letter stroke: a satin column of `w` mm, `h` tall, in mm, y down."""
    pts, y, left = [], y0, True
    while y <= y0 + h + 1e-9:
        pts.append((x0 if left else x0 + w, y))
        left, y = not left, y + pitch / 2
    return pts


def _write_dst(path, strokes, trims_before):
    """strokes: lists of mm points; a TRIM precedes stroke i for i in
    `trims_before`. One colour block."""
    import pystitch
    pat = pystitch.EmbPattern()
    for i, pts in enumerate(strokes):
        if i in trims_before:
            pat.add_command(pystitch.TRIM)
        x, y = pts[0]
        pat.add_stitch_absolute(pystitch.JUMP if i else pystitch.STITCH, x * 10, y * 10)
        for x, y in pts:
            pat.add_stitch_absolute(pystitch.STITCH, x * 10, y * 10)
    pat.add_command(pystitch.END)
    pystitch.write_dst(pat, str(path))
    return path


@pytest.fixture(scope="module")
def two_letters(tmp_path_factory):
    d = tmp_path_factory.mktemp("board")
    # letter 1 is two stacked strokes (a cut INSIDE the letter), letter 2 one stroke 3 mm to its
    # right (the cut between them is stage 7's order, not counted)
    strokes = [_column(10.0, 10.0, h=1.5), _column(10.0, 11.7, h=1.3), _column(14.0, 10.0, h=3.0)]
    return _write_dst(d / "word.dst", strokes, trims_before={1, 2})


def test_trims_inside_counts_a_cut_in_a_letter_and_not_one_between_letters():
    rows = [{"cls": "bare_letters", "a": [10.6, 11.5], "b": [10.6, 11.7]},     # inside letter 1
            {"cls": "bare_letters", "a": [10.6, 13.0], "b": [14.6, 10.0]},     # letter 1 -> letter 2
            {"cls": "colour", "a": [10.6, 11.5], "b": [10.6, 11.7]}]           # a colour change is not a cut
    boxes = [(10.0, 10.0, 11.2, 13.0), (14.0, 10.0, 15.2, 13.0)]
    assert lb.trims_inside(rows, boxes) == 1


def test_point_runs_rejoin_consecutive_segments_and_split_at_a_gap():
    segs = [(0, 0, 1, 0, 7, 0), (1, 0, 2, 0, 7, 1), (5, 5, 6, 5, 7, 4), (6, 5, 7, 5, 7, 5)]
    assert lb.point_runs(segs) == [[(0, 0), (1, 0), (2, 0)], [(5, 5), (6, 5), (7, 5)]]


def test_file_reader_reads_columns_width_stitches_and_the_one_cut_inside_a_letter(two_letters):
    reader = lb.FileReader(two_letters)
    got = reader.line((6.0, 6.0, 20.0, 17.0), 3.0, 11.5)
    assert got["read"]["n"] == 3                              # three letter-like pieces were the line
    assert got["columns"]["v"] == 3                          # letter 1's two strokes, letter 2's one
    assert got["satin_w"]["v"] == pytest.approx(1.2, abs=0.1)
    assert got["satin_w"]["w"] > 20                           # weighted by the crosses it read
    assert got["stitches"]["v"] > 30
    assert got["trims"]["v"] == 1                             # the cut inside letter 1; not the hop to letter 2


def test_file_reader_says_n_a_with_a_reason_for_a_line_that_is_not_there(two_letters):
    got = lb.FileReader(two_letters).line((60.0, 60.0, 80.0, 70.0), 3.0, 65.0)
    for key in ("columns", "stitches", "satin_w", "trims"):
        assert got[key]["v"] is None and got[key]["why"]


def test_file_reader_without_a_dst_has_no_trims_and_says_why(two_letters):
    got = lb.FileReader(two_letters, trim_why="no DST of the pro's").line((6.0, 6.0, 20.0, 17.0), 3.0, 11.5)
    assert got["trims"]["v"] is None and got["trims"]["why"] == "no DST of the pro's"
    assert got["columns"]["v"] is not None                    # the other figures do not depend on it


def test_rail_run_reads_a_straight_stem_on_its_outline_and_is_n_a_without_one(tmp_path):
    """`rail_run`: rail wobble p90 on the RUN windows only (`letter_band.rail_classes`)."""
    from shapely.geometry import box
    stem = _write_dst(tmp_path / "stem.dst", [_column(10.0, 10.0, h=12.0)], trims_before=set())
    reader = lb.FileReader(stem)
    got = reader.line((6.0, 6.0, 16.0, 26.0), 12.0, 16.0, box(10.0, 10.0, 11.2, 22.0))
    assert got["rail_run"]["v"] == pytest.approx(0.0, abs=1e-3)
    assert got["rail_run"]["w"] > 10                         # weighted by the run windows it read
    bare = reader.line((6.0, 6.0, 16.0, 26.0), 12.0, 16.0)
    assert bare["rail_run"]["v"] is None and "no text-tagged region" in bare["rail_run"]["why"]


def test_rail_run_of_a_line_too_short_for_a_window_is_n_a_not_zero(two_letters):
    from shapely.geometry import box
    got = lb.FileReader(two_letters).line((6.0, 6.0, 20.0, 17.0), 3.0, 11.5, box(10.0, 10.0, 15.2, 13.0))
    assert got["rail_run"]["v"] is None and "no run windows" in got["rail_run"]["why"]


def test_line_outline_is_our_text_regions_in_the_line_box():
    info = {"regions": [
        {"id": "a", "wkt": "POLYGON ((0 0, 2 0, 2 5, 0 5, 0 0))", "meta": {"text_candidate": True}},
        {"id": "b", "wkt": "POLYGON ((3 0, 5 0, 5 5, 3 5, 3 0))", "meta": {"word_id": "w1"}},
        {"id": "c", "wkt": "POLYGON ((0 0, 9 0, 9 5, 0 5, 0 0))", "meta": {}},                 # not text
        {"id": "d", "wkt": "POLYGON ((30 0, 32 0, 32 5, 30 5, 30 0))", "meta": {"text_candidate": True}}]}
    got = lb.line_outline(info, (0.0, 0.0, 6.0, 5.0))
    assert got.area == pytest.approx(20.0)                    # a and b; not the field, not the far letter
    assert lb.line_outline(info, (50.0, 50.0, 60.0, 60.0)) is None


def test_a_fragment_under_half_the_drawn_height_is_refused_and_called_a_fragment(tmp_path):
    small = _write_dst(tmp_path / "bit.dst", [_column(10.0, 10.0, h=3.0)], trims_before=set())
    got = lb.FileReader(small).line((5.0, 5.0, 20.0, 20.0), 8.0, 11.5)
    assert got["columns"]["v"] is None and "fragment of the line" in got["columns"]["why"]


def test_a_field_twenty_times_the_drawn_height_is_refused_not_scored(tmp_path):
    big = _write_dst(tmp_path / "field.dst", [_column(0.0, 0.0, h=60.0, w=1.2)], trims_before=set())
    got = lb.FileReader(big).line((-3.0, -3.0, 10.0, 63.0), 3.0, 30.0)
    assert got["columns"]["v"] is None and "blob" in got["columns"]["why"]


# --- end to end, on one small committed pair -----------------------------------------

def _pair_is_on_this_machine(slug):
    p = lb.resolve_pair(slug)
    return p.pro is not None and p.art is not None


@pytest.fixture(scope="module")
def becker_board(tmp_path_factory):
    """Becker's chest logo at its pro width, digitized and read: the one pair whose pro file
    (`testdata/reference`) and artwork are committed, so it runs in CI."""
    slug = "becker_chest_small"
    if not _pair_is_on_this_machine(slug):
        pytest.skip("Becker's chest files are not on this machine")
    cache = tmp_path_factory.mktemp("board_cache")
    # White pinned OFF: with `sew_enclosed_white` (ON since 2026-10-26) BECKER's white
    # faces are the block with the most letter-like thread, so `read_element` reads the
    # faces' fill (one 0.43 mm "column") instead of the letters' outline -- the board's
    # own limitation on hollow lettering, reported in #1112, not what this smoke pins.
    sets = {"sew_enclosed_white": False}
    lb.prepare_cache(cache, sets)
    lb.digitize_missing([slug], cache, sets, log=lambda *_: None)
    return lb.build([slug], cache, sets, ocr=True, date="2026-10-25", log=lambda *_: None)


def test_smoke_the_board_reads_both_lines_of_becker_in_both_files(becker_board):
    lines = becker_board["lines"]
    assert [l["text"] for l in lines] == ["BECKER", "MARINE"]
    for ln in lines:
        assert ln["band"] == "10+" and ln["slug"] == "becker_chest_small"
        assert ln["read"]["ours"]["h_mm"] and ln["read"]["pro"]["h_mm"]       # both files found the line
        for side in ("ours", "pro"):
            assert ln[side]["columns"]["v"] > 0 and ln[side]["stitches"]["v"] > 200
            assert 0.5 < ln[side]["satin_w"]["v"] < 5.0


def test_smoke_every_figure_is_a_number_or_an_n_a_with_a_reason(becker_board):
    for ln in becker_board["lines"]:
        for side in ("ours", "pro"):
            for key in lb.METRICS:
                s = ln[side][key]
                assert (s["v"] is not None) != bool(s["why"]), (ln["text"], side, key, s)


def test_smoke_the_cell_pools_the_lines_and_the_json_round_trips(becker_board):
    cell = becker_board["cells"]["becker_chest_small"]["10+"]
    assert cell["lines"] == ["BECKER", "MARINE"]
    assert cell["columns"]["n"] == 2 and cell["columns"]["ours"] > 0
    again = json.loads(json.dumps(becker_board))
    md = lb.render_md(again)
    assert "becker_chest_small | 10+" in md
    # the board against itself: nothing moved
    assert "No change in any cell." in lb.compare_boards(again, again)


# --- word legibility, per line ---------------------------------------------------------

def _row(cc, raw=0.9):
    return {"cc": cc, "raw": raw}


def test_a_lines_cc_is_over_the_words_both_files_scored_weighted_by_letters():
    got = {"HOTEL": {"ours": _row(1.0), "pro": _row(0.5), "why": {}},
           "FREMONT": {"ours": _row(0.0), "pro": _row(1.0), "why": {}},
           "EST": {"ours": _row(1.0), "pro": None, "why": {"pro": "not located: best match costs 2.3 (> 2.0)"}}}
    o, p = lb.line_cc(["HOTEL", "FREMONT", "EST"], got)
    assert o["w"] == p["w"] == 12                                  # EST is in neither sum: the pro never read it
    assert o["v"] == pytest.approx((1.0 * 5 + 0.0 * 7) / 12, abs=1e-3)
    assert p["v"] == pytest.approx((0.5 * 5 + 1.0 * 7) / 12, abs=1e-3)


def test_a_lines_reach_is_the_same_mean_over_the_words_both_files_have_a_reach_for():
    r = lambda cc, reach: {"cc": cc, "raw": 0.9, "reach": reach}          # noqa: E731
    got = {"HOTEL": {"ours": r(1.0, 4.0), "pro": r(1.0, 3.0), "why": {}},
           "FREMONT": {"ours": r(1.0, 2.0), "pro": r(1.0, 5.0), "why": {}},
           "EST": {"ours": r(1.0, None), "pro": r(1.0, 2.0), "why": {}}}   # no ladder was read for ours' EST
    o, p = lb.line_cc(["HOTEL", "FREMONT", "EST"], got, "reach")
    assert o["w"] == p["w"] == 12                                          # EST is in neither: one file has no reach
    assert o["v"] == pytest.approx((4.0 * 5 + 2.0 * 7) / 12, abs=1e-3)
    assert p["v"] == pytest.approx((3.0 * 5 + 5.0 * 7) / 12, abs=1e-3)
    both = lb.line_cc(["EST"], got, "reach")[0]
    assert both["v"] is None and "EST: no reach in ours" in both["why"]
    assert lb.line_cc(["HOTEL", "FREMONT"], got)[0]["v"] == pytest.approx(1.0)       # the default is still cc


def test_the_reach_column_is_a_board_metric_and_an_old_board_without_it_still_renders():
    assert lb.METRICS["reach"][1] == "mean"
    cells = lb.cells(sample_lines())
    assert cells["ALL"]["<4"]["reach"]["ours"] is None and cells["ALL"]["<4"]["reach"]["why"] == "not read"
    board = {"meta": {"date": "2026-10-25"}, "lines": sample_lines(),
             "cells": {k: {b: {m: v for m, v in c.items() if m != "reach"} for b, c in bands.items()}
                       for k, bands in cells.items()}}
    md = lb.render_md(board)                      # a board written before `reach` existed has no cell for it
    assert "word legibility reach (octaves)" in md and "not on this board" in md


def test_a_line_whose_words_nobody_scored_is_n_a_and_names_each_word_and_file():
    got = {"EST": {"ours": _row(1.0), "pro": None, "why": {"pro": "not located: best match costs 2.3 (> 2.0)"}}}
    o, p = lb.line_cc(["EST"], got)
    assert o["v"] is None and p["v"] is None
    assert "EST: pro not located" in o["why"]


def test_a_line_with_no_pinned_words_is_n_a_not_zero():
    o, p = lb.line_cc([], {})
    assert o["v"] is None and "no words pinned" in o["why"]


# --- the cache and the proposer ------------------------------------------------------------

def test_a_cache_refuses_a_different_flag_set(tmp_path):
    lb.prepare_cache(tmp_path, {})
    lb.prepare_cache(tmp_path, {})                                  # the same set again is fine
    with pytest.raises(SystemExit, match="made with flags"):
        lb.prepare_cache(tmp_path, {"cut_every_jump": True})


def test_the_board_names_the_engine_that_made_the_cached_files_not_the_tree_it_is_read_in(tmp_path):
    (tmp_path / lb.CACHE_RECORD).write_text(json.dumps({"sets": {}, "git": "abc1234"}), encoding="utf-8")
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    (tmp_path / "b" / lb.ENGINE_STAMP).write_text("def5678", encoding="utf-8")
    assert lb.cache_engine(tmp_path, ["a"]) == "abc1234"                  # no stamp: the record's
    assert lb.cache_engine(tmp_path, ["a", "b"]) == "abc1234, def5678"    # a cache two commits wide says so


def test_a_cache_with_files_and_no_record_is_refused_unless_trusted(tmp_path):
    (tmp_path / "becker_hat_small").mkdir()
    with pytest.raises(SystemExit, match="does not say which flags"):
        lb.prepare_cache(tmp_path, {})
    lb.prepare_cache(tmp_path, {}, trust=True)
    assert json.loads((tmp_path / lb.CACHE_RECORD).read_text())["sets"] == {}


def test_a_pair_that_could_not_be_digitized_is_listed_with_its_reason_not_fatal(tmp_path):
    board = lb.build(["becker_hat_small"], tmp_path, {}, ocr=False, date="2026-10-25",
                     log=lambda *_: None, failed={"becker_hat_small": "missing pro file"})
    assert {"slug": "becker_hat_small", "why": "not digitized: missing pro file"} in board["meta"]["skipped"]
    assert board["lines"] == []
    # every pair without pinned lines is listed too, so the board says what it does not cover
    listed = {s["slug"]: s["why"] for s in board["meta"]["skipped"]}
    off = {r[0] for r in lb.pair_rows()} - set(lb.load_lines())
    assert off <= set(listed)
    for slug in off:
        assert listed[slug] == lb.load_left_off().get(slug) or listed[slug].startswith("no lettering lines pinned")


def test_only_a_pair_with_pinned_lines_can_be_asked_for(tmp_path):
    with pytest.raises(SystemExit, match="no lines pinned for that pair"):
        lb.main(["--cache", str(tmp_path), "--only", "not_a_pair"])


def _region(x0, y0, x1, y1, cluster):
    from shapely.geometry import box
    return {"id": "r", "wkt": box(x0, y0, x1, y1).wkt, "meta": {"text_cluster_id": cluster}}


def test_candidate_rows_split_a_cluster_by_line_and_report_the_drawn_height():
    regs = [_region(0, 0, 3, 5, "TCa"), _region(4, 0, 7, 5, "TCa"),            # one row, 5 mm tall
            _region(0, 8, 3, 10, "TCa"), _region(4, 8, 7, 10, "TCa"),          # a second row, 2 mm
            _region(20, 0, 22, 4, "TCb"), _region(30, 0, 33, 4, None)]          # untagged: never a candidate
    rows = lb.candidate_rows({"regions": regs})
    assert [(r["cluster"], r["n"], r["art_h"]) for r in rows] == [("TCa", 2, 5.0), ("TCb", 1, 4.0), ("TCa", 2, 2.0)]
    assert rows[0]["box"] == [0.0, 0.0, 7.0, 5.0]


def test_the_command_line_prints_the_delta_of_two_saved_boards(tmp_path, capsys):
    a, b = board_of(sample_lines()), board_of(sample_lines())
    b["lines"][0]["ours"]["columns"] = slot(5)
    b["cells"] = lb.cells(b["lines"])
    pa, pb = tmp_path / "a.json", tmp_path / "b.json"
    pa.write_text(json.dumps(a), encoding="utf-8")
    pb.write_text(json.dumps(b), encoding="utf-8")
    assert lb.main(["--compare", str(pa), str(pb)]) == 0
    assert "| fremont_hat | <4 | columns | 1 -> 6 | +5 |" in capsys.readouterr().out
