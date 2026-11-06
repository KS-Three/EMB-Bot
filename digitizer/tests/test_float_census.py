"""`tools/float_census.py` (2026-11-06, defect 4): the move classifier on a
hand-built DST, the `cut_every_jump` replay's per-float rows on a synthetic
plan, and the three break definitions' arithmetic.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pystitch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from digitizer_core import stitches  # noqa: E402
from digitizer_core.stitches import StitchBlock, StitchRun  # noqa: E402
from tools import float_census as fc  # noqa: E402

from .proloop_synth import fill_passes  # noqa: E402

WALK_Y = 3.1


def _box(x0, y0=0.0, w=4.0, h=6.0):
    return [p for row in fill_passes(x0, y0, w, h) for p in row]


def _write(path, blocks):
    """`blocks`: [(rgb, [(move, pts), ...])], move one of "first", "jump"
    (needle-up, no trim), "trim" (TRIM then JUMP) or "down" (needle-down
    straight into the pass). Units 0.1 mm."""
    pat = pystitch.EmbPattern()
    for rgb, _ in blocks:
        t = pystitch.EmbThread()
        t.set_color(*rgb)
        pat.add_thread(t)
    last = None
    for bi, (_rgb, passes) in enumerate(blocks):
        if bi:
            pat.add_stitch_absolute(pystitch.COLOR_CHANGE, *_u(passes[0][1][0]))
        for move, pts in passes:
            if move == "trim":
                pat.add_stitch_absolute(pystitch.TRIM, *_u(last))
                pat.add_stitch_absolute(pystitch.JUMP, *_u(pts[0]))
            elif move == "jump":
                pat.add_stitch_absolute(pystitch.JUMP, *_u(pts[0]))
            for p in pts:
                pat.add_stitch_absolute(pystitch.STITCH, *_u(p))
            last = pts[-1]
    pat.end()
    pystitch.write_dst(pat, str(path))
    return path


def _u(p):
    return int(round(p[0] * 10)), int(round(p[1] * 10))


def test_dst_moves_reads_cut_uncut_and_walked(tmp_path):
    """Four letter boxes in one colour: A, an uncut 2 mm float to B, a cut
    to C, a needle-down walk to D. The block's opening lift is a colour
    change and is not counted."""
    a = _box(0.0) + [(4.0, WALK_Y)]
    b = [(6.0, WALK_Y)] + _box(6.0)
    c = _box(20.0) + [(24.0, WALK_Y)]
    d = [(30.0, WALK_Y)] + _box(30.0)
    dst = _write(tmp_path / "moves.dst", [((30, 30, 30), [("first", a), ("jump", b), ("trim", c),
                                                           ("down", [(27.0, WALK_Y)] + d)])])
    m = fc.dst_moves(dst)
    assert (m["cuts"], m["uncut"], m["walked"]) == (1, 1, 1)
    assert m["uncut_mm"] == [2.0] and m["cut_mm"] == [round(math.dist(b[-1], c[0]), 2)]
    # 6 mm walked on fabric; the 0.4 mm end allowance at each end reads as buried
    assert m["walked_mm"] == 6.0 and 5.0 <= m["walked_bare_mm"] <= 5.4
    assert m["trim_classes"]["bare_letters"] == 1
    assert m["inpiece_cuts"] == 0


def test_dst_moves_on_a_committed_pro_file():
    """The pro cuts every needle-up move on his Becker hat: a reader that
    agreed with `sequence_pro` on 2026-11-06."""
    m = fc.dst_moves(HERE.parent / "testdata" / "reference" / "becker_hat_polo_large_beckers_logo_hat.dst")
    assert m["uncut"] == 0 and m["cuts"] == 9 and m["walked"] == 0
    assert fc.breaks(m["cuts"], m["uncut"]) == {"A_cut_plus_uncut": 9, "B_cut": 9,
                                                "C_cut_plus_uncut_not_walked": 9}


# --- the replay ---------------------------------------------------------------

def _rows(x0, x1, y0, n, shape="C"):
    pts = []
    for i in range(n):
        y = y0 + i * 0.15
        pts += [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
    return [StitchRun(points=pts, kind=stitches.FILL, jump=True, trim=True, shape_id=shape)]


def _hop(y, tag):
    p = StitchRun(points=[(-1.0, y), (0.0, y)], kind=stitches.FILL, shape_id=f"A{tag}",
                  jump=True, trim=True)
    q = StitchRun(points=[(2.0, y), (3.0, y)], kind=stitches.FILL, jump=True, shape_id=f"B{tag}")
    return p, q


def _block(thread, runs, rgb=None):
    return StitchBlock(thread_index=thread, thread_number=f"{1000 + thread}",
                       rgb=rgb or (thread, thread, thread), runs=runs)


def _four_floats():
    """One colour block (0) with four 2 mm floats: under rows it sews LATER
    (buried); on rows a WHITE block sewed earlier (walked, white field); on
    rows another colour sewed earlier (walked, other); on its own earlier
    rows (walked, same colour); and a fifth over nothing (cut, bare)."""
    a1, b1 = _hop(0.0, "buried")
    a2, b2 = _hop(20.0, "white")
    a3, b3 = _hop(40.0, "other")
    a4, b4 = _hop(60.0, "same")
    a5, b5 = _hop(80.0, "bare")
    blocks = [_block(1, _rows(-1.0, 3.0, 18.5, 21), rgb=(255, 255, 255)),
              _block(2, _rows(-1.0, 3.0, 38.5, 21), rgb=(200, 30, 30)),
              _block(0, _rows(-1.0, 3.0, 58.5, 21, shape="own") + [a1, b1] + _rows(-1.0, 3.0, -1.5, 21)
                     + [a2, b2, a3, b3, a4, b4, a5, b5])]
    return blocks


def test_replay_records_each_float_with_the_engines_outcome_and_what_it_lies_on():
    blocks = _four_floats()
    rows, counts = fc.replay(blocks)
    assert counts == (1, 3, 1)
    by = {r["to_shape"]: r for r in rows}
    assert len(rows) == 5 and all(r["len_mm"] == 2.0 and r["block"] == 2 for r in rows)
    assert (by["Bburied"]["outcome"], by["Bburied"]["lies_on"]) == ("buried", "same")
    assert (by["Bwhite"]["outcome"], by["Bwhite"]["lies_on"]) == ("walked", "white")
    assert (by["Bother"]["outcome"], by["Bother"]["lies_on"]) == ("walked", "other")
    assert (by["Bsame"]["outcome"], by["Bsame"]["lies_on"]) == ("walked", "same")
    assert (by["Bbare"]["outcome"], by["Bbare"]["lies_on"]) == ("cut", "bare")
    assert by["Bbare"]["bare_frac"] > 0.5 and by["Bwhite"]["white_frac"] > 0.5
    # the engine mutated the plan as the pass does: the bare one is cut, the rest sewn down
    seq = [r for b in blocks for r in b.runs]
    assert sum(1 for r in seq if r.jump and not r.trim) == 0


def test_replay_fine_is_the_same_pass_at_the_fine_step():
    """Rows 0.15 mm apart leave no gap at either step, so the outcomes agree;
    the step itself is pinned in `test_bury_step_fine`."""
    coarse, fine = _four_floats(), _four_floats()
    rc, cc = fc.replay(coarse)
    rf, cf = fc.replay(fine, fine=True)
    assert cc == cf == (1, 3, 1)
    assert [(r["to_shape"], r["outcome"]) for r in rc] == [(r["to_shape"], r["outcome"]) for r in rf]


def test_plan_floats_keeps_the_finished_plans_rows_only():
    """Stage 7 runs the pass once more on a trial sub-layout inside a plan
    (`column_lean`), so a float can be recorded twice; the rows kept are
    the ones whose run the finished plan sews."""
    from digitizer_core.stitches import StitchPlan
    trial, final = _four_floats(), _four_floats()
    rows = []
    with fc.recording(rows):
        from digitizer_core import stage7_sequence as s7
        s7._cut_or_bury_jumps(trial)
        s7._cut_or_bury_jumps(final)
    assert len(rows) == 10
    kept = fc.plan_floats(rows, StitchPlan(blocks=final, palette=[], warnings=[]))
    assert len(kept) == 5 and all("_run" not in r for r in kept)
    assert {r["to_shape"] for r in kept} == {"Bburied", "Bwhite", "Bother", "Bsame", "Bbare"}


def test_recording_restores_the_engine(monkeypatch):
    from digitizer_core import stage7_sequence as s7
    real_pass, real_burier = s7._cut_or_bury_jumps, s7._later_thread_burier
    rows = []
    with fc.recording(rows):
        assert s7._cut_or_bury_jumps is not real_pass
        s7._cut_or_bury_jumps(_four_floats())
        assert s7._later_thread_burier is real_burier, "the burier is wrapped only inside the pass"
    assert s7._cut_or_bury_jumps is real_pass and s7._later_thread_burier is real_burier
    assert len(rows) == 5


# --- the three definitions ----------------------------------------------------

def test_breaks_three_ways():
    # the 10-29 doc's pooled figures: ours 391 cuts + 488 uncut, the pro 409 + 16
    ours, pro = fc.breaks(391, 488, walked_floats=300), fc.breaks(409, 16)
    assert ours == {"A_cut_plus_uncut": 879, "B_cut": 391, "C_cut_plus_uncut_not_walked": 579}
    assert pro == {"A_cut_plus_uncut": 425, "B_cut": 409, "C_cut_plus_uncut_not_walked": 425}


def test_job_summary_reads_the_off_arms_walked_floats_from_the_on_arm():
    moves = lambda cuts, uncut, walked=0: {"cuts": cuts, "uncut": uncut, "walked": walked, "walked_mm": 0.0,
                                           "inpiece_cuts": 0,
                                           "trim_classes": {k: 0 for k in ("colour", "under_later", "on_work",
                                                                           "bare_letters", "bare_other")}}
    cell = lambda cuts, uncut, **kw: {"moves": moves(cuts, uncut), "exposed_mm": 1.0, "bare_mm_020": 0.5,
                                      "plan_cpu_s": 2.0, "md5": "x", **kw}
    rep = {"slug": "j", "pro": moves(9, 0), "arms": {
        "off": cell(12, 8),
        "on": cell(15, 0, floats=8, outcomes={"buried": 1, "walked": 4, "cut": 3},
                   lies_on={"same": 2, "white": 3, "other": 0, "bare": 3})}}
    s = fc.job_summary(rep)
    assert s["off"]["C_cut_plus_uncut_not_walked"] == 12 + 8 - 4 and s["off"]["A_cut_plus_uncut"] == 20
    assert s["on"]["A_cut_plus_uncut"] == s["on"]["B_cut"] == 15
    assert s["pro"]["A_cut_plus_uncut"] == 9
    pool = fc.pooled([s, s])
    assert pool["off"]["A_cut_plus_uncut"] == 40 and pool["on"]["outcomes"]["walked"] == 8
    md = fc.markdown([s], ["mfab_hat"], pool)
    assert "| j | pro | 9 | 0 | 0 | 0 | 9 | 9 | 9 |" in md and "n/a here" in md and "mfab_hat" in md


def test_arm_config_flags():
    from digitizer_core import PipelineConfig
    base = PipelineConfig()
    assert fc.arm_config(base, "off") is base
    on, fine = fc.arm_config(base, "on"), fc.arm_config(base, "on_fine")
    assert on.cut_every_jump and not on.extra.get("bury_step_fine")
    assert fine.cut_every_jump and fine.extra["bury_step_fine"] is True
    assert not base.cut_every_jump and not base.extra
