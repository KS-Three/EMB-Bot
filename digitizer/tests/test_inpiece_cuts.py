"""`tools/inpiece_cuts.py` -- why a file cuts inside one sewn piece, pinned on
hand-built plans and DSTs, so the classes mean what the W4 table says."""
from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace as NS

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from tools import inpiece_cuts as ic  # noqa: E402
from tools import sequence_pro as sp  # noqa: E402

from .proloop_synth import fill_passes, satin_pass, write_pattern  # noqa: E402


def _run(pts, kind, sid, trim=False):
    return NS(points=[tuple(p) for p in pts], kind=kind, shape_id=sid, jump=trim, trim=trim)


def _rows(x0, y0, w, h):
    """One serpentine fill pass over a box (rows joined)."""
    return [p for row in fill_passes(x0, y0, w, h) for p in row]


def _plan(*runs):
    return NS(blocks=[NS(runs=list(runs))])


def test_a_cut_between_two_sections_of_one_fill_is_fill_section():
    """Two halves of one fill touch (one piece); the needle cuts from the
    end of the first to the start of the second."""
    plan = _plan(_run(_rows(0, 0, 10, 4), "fill", "S1"),
                 _run(_rows(0, 4.4, 10, 4)[::-1], "fill", "S1", trim=True))
    rows = ic.classify_plan(plan)
    assert [r["cause"] for r in rows] == ["fill_section"]


def test_an_underlay_restart_counts_for_its_satin():
    """Satin, cut, the next stroke's centre run, its satin: a split satin
    restarting (the underlay stands for the column it carries)."""
    a = satin_pass(0, 0, 10, 2)                       # the T's bar
    under = [(5.0, 0.5 + 1.0 * i) for i in range(9)]  # the stem's centre run
    b = satin_pass(5.0, 0.0, 8, 2, angle_deg=90.0)     # ...and its column
    plan = _plan(_run(a, "satin", "S1"), _run(under, "underlay", "S1", trim=True),
                 _run(b, "satin", "S1"))
    assert [r["cause"] for r in ic.classify_plan(plan)] == ["satin_split"]


def test_two_shapes_and_the_edge_cap():
    fill = _rows(0, 0, 10, 4)
    plan = _plan(_run(fill, "fill", "S1"),
                 _run(_rows(0, 4.4, 10, 4), "fill", "S2", trim=True),
                 _run([(0.0, 0.2), (3.0, 0.2), (6.0, 0.2), (9.0, 0.2)], "run", "__edge_cap__",
                      trim=True))
    assert sorted(r["cause"] for r in ic.classify_plan(plan)) == ["edge_cap", "shape_to_shape"]


def test_a_cut_between_pieces_is_not_counted():
    plan = _plan(_run(_rows(0, 0, 4, 4), "fill", "S1"),
                 _run(_rows(20, 0, 4, 4), "fill", "S1", trim=True))
    assert ic.classify_plan(plan) == []


def test_the_dst_reader_matches_sequence_pro_and_reads_stitch_character(tmp_path):
    """A satin column, cut, a centre run and a satin column on top of it --
    one piece: one cut inside it, satin before, run after. The same file's
    `sequence_pro` inside count agrees."""
    col = satin_pass(0, 0, 18, 2)
    run = [(1.5 * i, 0.0) for i in range(13)]
    col2 = satin_pass(0, 0, 18, 2)
    path = write_pattern(tmp_path / "p.dst", [((200, 30, 30), [col, run + col2])])
    rows = ic.classify_dst(path)
    total = sp.read_file(path)["total"]
    assert len(rows) == total["trims"] - total["inter_trims"] == 1
    assert rows[0]["before"] == "satin" and rows[0]["after"] == "run"


def test_character():
    def mv(pts):
        return [{"p": p, "up": False, "trim": False} for p in pts]
    assert ic.character(mv(satin_pass(0, 0, 8, 2)), 0, 12) == "satin"
    assert ic.character(mv([(2.0 * i, 0.0) for i in range(12)]), 0, 12) == "run"
    assert ic.character(mv([(3.5 * i, 0.0) for i in range(12)]), 0, 12) == "fill"
