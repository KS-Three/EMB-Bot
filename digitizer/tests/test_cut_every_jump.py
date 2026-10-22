"""`cfg.cut_every_jump` (built OFF 2026-10-21): no needle-up move is left
uncut. Each jump that would not cut is sewn needle-down where thread sewn
LATER hides all of it, and cut, locked on both sides, everywhere else.

The pro's 28 DSTs leave no needle-up move uncut; ours left 0-168 jumps of
0.5-3.0 mm per job (`docs/settings-vs-pro-2026-10-21.md` row 25). The
cover rule is `trim_bury_under_later`'s, shared code, so this file reuses
that file's independent re-measure of buried travel rather than a second
copy of it.
"""
from __future__ import annotations

import json
from dataclasses import replace

import pytest

from digitizer_core import PipelineConfig, stitches
from digitizer_core import stage7_sequence
from digitizer_core.stage7_sequence import _cut_or_bury_jumps
from digitizer_core.stitches import StitchBlock, StitchRun

from .test_trim_bury_under_later import _bar, _md5, _plan, _region, _travel_is_hidden


def _new_travel(off_blocks, on_blocks):
    """(flat ON sew order, indices of the travel runs ON added). A travel
    run OFF already sewed counts as old even when this flag locked it -- a
    tie-off appended to it, a tie-in put in front -- since only the travel
    this pass ADDS is under test."""
    by_head: dict = {}
    for b in off_blocks:
        for r in b.runs:
            if r.kind == stitches.TRAVEL and r.points:
                t = tuple(map(tuple, r.points))
                by_head.setdefault(t[0], []).append(t)

    def old(pts):
        return any(pts[i:i + len(t)] == t
                   for i, p in enumerate(pts) for t in by_head.get(p, ()))

    seq = [r for b in on_blocks for r in b.runs]
    return seq, [k for k, r in enumerate(seq) if r.kind == stitches.TRAVEL
                 and not old(tuple(map(tuple, r.points)))]


def _new_hops(off_blocks, on_blocks):
    """(flat ON sew order, [(k, needle-down path)]) for every hop this flag
    sewed: each travel run it added, from the stitch before to the one
    after, and each jump it sewed as one plain stitch (a hop no longer than
    a link stitch gets no travel run: the needle just goes down at the next
    run's start)."""
    seq, new = _new_travel(off_blocks, on_blocks)
    out = [(k, [seq[k - 1].points[-1]] + list(seq[k].points) + [seq[k + 1].points[0]], False)
           for k in new]
    jumped = {tuple(map(tuple, r.points)) for b in off_blocks for r in b.runs if r.jump}
    for k, r in enumerate(seq):
        if (k and not r.jump and r.kind != stitches.TRAVEL and r.points
                and seq[k - 1].kind != stitches.TRAVEL and seq[k - 1].points
                and tuple(map(tuple, r.points)) in jumped):
            out.append((k, [seq[k - 1].points[-1], r.points[0]], True))
    return seq, out


def _hop_hidden(seq, k, path, direct) -> bool:
    """`_travel_is_hidden` for either kind of sewn hop. A direct hop is the
    head of run k, so run k's own stitches (not the hop) count as later:
    it is read as still lifted, so its thread does not include the hop."""
    if not direct:
        return _travel_is_hidden(seq, k, path)
    run = seq[k]
    run.jump = True
    try:
        return _travel_is_hidden(seq, k - 1, path)
    finally:
        run.jump = False


def _near_bars(bridge_layer=None, **kw):
    """Two same-colour bars 2 mm apart -- under the 3.0 mm trim distance, so
    the hop between them is an uncut jump -- with an optional other-colour
    bridge over the gap, sewn before (0) or after (1) the bars."""
    bars_layer = 1 if bridge_layer == 0 else 0
    regions = [_region(_bar(0, 10), bars_layer, "Sleft", 0),
               _region(_bar(12, 22), bars_layer, "Sright", 0)]
    if bridge_layer is not None:
        regions.append(_region(_bar(10, 12), bridge_layer, "Sbridge", 1))
    return _plan(regions, **kw)


def _crossing(blocks):
    for b in blocks:
        runs = b.runs
        for i, run in enumerate(runs):
            if i and {run.shape_id, runs[i - 1].shape_id} == {"Sleft", "Sright"}:
                return runs, i
    raise AssertionError("the plan never got from one bar to the other")


def _uncut(blocks) -> int:
    """Needle-up moves with no cut, the first run of each block (a colour
    change) aside -- the count the DST reads."""
    return sum(1 for b in blocks for i, r in enumerate(b.runs)
               if i and r.points and r.jump and not r.trim)


def _locked_head(run) -> bool:
    """`tie_run`'s bounce: the run's head revisits a point."""
    head = run.points[:5]
    return len(set(head)) < len(head)


# --- OFF: byte-identical, and the new code is never reached ----------------

# Captured on the base commit (03ccab4e), before the flag existed.
OFF_MD5 = {"bare": "46bede5a3d93e11a2a425893b0881e3a",
           "later": "ecc016d499270d4af4c33694b1afefe6",
           "earlier": "d9cad9b85d5cd8627a800be40642dd84"}


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("cut_every_jump code reached with the flag off")
    monkeypatch.setattr(stage7_sequence, "_cut_or_bury_jumps", boom)
    _near_bars(bridge_layer=1)
    _near_bars()


@pytest.mark.parametrize("case,layer", [("bare", None), ("later", 1), ("earlier", 0)])
def test_off_is_byte_identical_to_base(case, layer):
    assert _md5(_near_bars(bridge_layer=layer)) == OFF_MD5[case]


def test_the_fixture_has_an_uncut_jump_with_the_flag_off():
    runs, i = _crossing(_near_bars())
    assert runs[i].jump and not runs[i].trim, "precondition: a 2 mm hop is not cut"


# --- ON: bury first, otherwise cut -------------------------------------------

def test_a_jump_later_thread_buries_is_sewn_needle_down():
    runs, i = _crossing(_near_bars(bridge_layer=1, cut_every_jump=True))
    assert runs[i].kind == stitches.TRAVEL and not runs[i].jump and not runs[i].trim


def test_a_jump_over_bare_fabric_is_cut_and_locked_both_sides():
    runs, i = _crossing(_near_bars(cut_every_jump=True))
    assert runs[i].trim and runs[i].jump
    assert _locked_head(runs[i]), "the thread starts again here: a tie-in"
    tail = runs[i - 1].points[-5:]
    assert len(set(tail)) < len(tail), "the thread is cut here: a tie-off"


def _rows(x0, x1, y0, n):
    """One fill run of `n` back-and-forth rows 0.15 mm apart from y0: no
    needle-up move of its own, so the hop is the only one under test."""
    pts = []
    for i in range(n):
        y = y0 + i * 0.15
        pts += [(x0, y), (x1, y)] if i % 2 == 0 else [(x1, y), (x0, y)]
    return [StitchRun(points=pts, kind=stitches.FILL, jump=True, trim=True, shape_id="C")]


def _hop():
    """A 2 mm needle-up hop the plan did not cut: (run before, the jump)."""
    a = StitchRun(points=[(-1.0, 0.0), (0.0, 0.0)], kind=stitches.FILL, shape_id="A")
    b = StitchRun(points=[(2.0, 0.0), (3.0, 0.0)], kind=stitches.FILL,
                  jump=True, shape_id="B")
    return a, b


def _block(thread, runs):
    return StitchBlock(thread_index=thread, thread_number=f"{1000 + thread}",
                       rgb=(thread, thread, thread), runs=runs)


def test_a_jump_over_thread_already_sewn_is_cut():
    """Rows over the gap sew FIRST, in another block: travel across them
    would lie on finished work, so the jump is cut, not sewn."""
    a, b = _hop()
    blocks = [_block(1, _rows(-1.0, 3.0, -1.5, 21)), _block(0, [a, b])]
    assert _cut_or_bury_jumps(blocks) == (0, 1)
    assert b.trim and b.jump


def test_a_jump_under_rows_sewn_later_is_sewn_down():
    a, b = _hop()
    block = _block(0, [a, b] + _rows(-1.0, 3.0, -1.5, 21))
    assert _cut_or_bury_jumps([block]) == (1, 0)
    # 2 mm is one link stitch: the needle simply goes down at b's start
    assert not b.jump and not b.trim and block.runs[1] is b


def test_a_jump_under_another_colour_sewn_later_is_sewn_down():
    a, b = _hop()
    assert _cut_or_bury_jumps([_block(0, [a, b]), _block(1, _rows(-1.0, 3.0, -1.5, 21))]) == (1, 0)


def test_a_bare_jump_is_cut_with_both_locks():
    a, b = _hop()
    n_a, n_b = len(a.points), len(b.points)
    assert _cut_or_bury_jumps([_block(0, [a, b])]) == (0, 1)
    assert b.trim and len(a.points) > n_a and len(b.points) > n_b
    assert _locked_head(b)


@pytest.mark.parametrize("layer", [None, 1])
def test_no_needle_up_move_is_left_uncut(layer):
    assert _uncut(_near_bars(bridge_layer=layer)) > 0
    assert _uncut(_near_bars(bridge_layer=layer, cut_every_jump=True)) == 0


def test_a_cut_already_there_is_left_alone():
    """A trimmed hop is `trim_bury_under_later`'s, not this pass's."""
    a = StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=stitches.FILL, shape_id="A")
    b = StitchRun(points=[(5.0, 0.0), (6.0, 0.0)], kind=stitches.FILL,
                  jump=True, trim=True, shape_id="B")
    rows = [StitchRun(points=[(-1.0, y), (7.0, y)], kind=stitches.FILL, shape_id="C")
            for y in [i * 0.15 - 1.5 for i in range(21)]]
    block = StitchBlock(thread_index=0, thread_number="1000", rgb=(0, 0, 0),
                        runs=[a, b] + rows)
    before = [list(r.points) for r in block.runs]
    assert _cut_or_bury_jumps([block]) == (0, 0)
    assert [list(r.points) for r in block.runs] == before and b.trim


def test_a_colour_change_is_never_touched():
    a = StitchBlock(thread_index=0, thread_number="1000", rgb=(0, 0, 0),
                    runs=[StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=stitches.FILL)])
    first = StitchRun(points=[(2.0, 0.0), (3.0, 0.0)], kind=stitches.FILL, jump=True)
    b = StitchBlock(thread_index=1, thread_number="1001", rgb=(9, 9, 9), runs=[first])
    assert _cut_or_bury_jumps([a, b]) == (0, 0)
    assert not first.trim


# --- the invariant: no buried travel shows -----------------------------------

@pytest.mark.parametrize("layer", [1, None, 0])
def test_no_buried_travel_lies_outside_later_thread(layer):
    off = _near_bars(bridge_layer=layer)
    on = _near_bars(bridge_layer=layer, cut_every_jump=True)
    seq, hops = _new_hops(off, on)
    for k, path, direct in hops:
        assert _hop_hidden(seq, k, path, direct), f"hop at {k} shows"


@pytest.fixture(scope="module")
def roofing_hat():
    """Gaulke Roofing at the pro's hat width (114.2 mm, `c golke logo
    hat.DST`) through the Studio's request, planned three ways from one
    generation: off, this flag, and this flag with `trim_bury_under_later`.
    Measured 2026-10-21: 23 uncut jumps off; on, 22 cut and 1 sewn down."""
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools.pro_pair import request
    from .conftest import TESTDATA
    data = (TESTDATA / "art" / "logo_golke_roofing.png").read_bytes()
    conf = PipelineConfig(**_parse_config(json.dumps(request(114.2, "hat_front"))))
    gen = build_generation(_decode(data), conf, exif_source=data)
    out = {}
    for name, kw in (("off", {}), ("on", {"cut_every_jump": True}),
                     ("both", {"cut_every_jump": True, "trim_bury_under_later": True})):
        c = replace(conf, **kw)
        out[name] = plan_stitches(finish_generation(gen.fork(), c), c).blocks
    return out


def test_committed_artwork_leaves_no_uncut_jump_and_no_travel_shows(roofing_hat):
    off, on = roofing_hat["off"], roofing_hat["on"]
    assert _uncut(off) > 0, "the fixture no longer has an uncut jump to remove"
    assert _uncut(on) == 0
    seq, hops = _new_hops(off, on)
    assert hops, "nothing sewn down: the fixture no longer exercises the bury"
    for k, path, direct in hops:
        assert _hop_hidden(seq, k, path, direct), f"roofing: hop {k} shows"


def test_composes_with_trim_bury_under_later(roofing_hat):
    """Both ON: still no uncut jump, and no more cuts than this flag alone --
    the earlier pass only ever turns cuts into hidden travel."""
    on, both = roofing_hat["on"], roofing_hat["both"]
    assert _uncut(both) == 0
    trims = lambda blocks: sum(r.trim for b in blocks for r in b.runs)
    assert trims(both) <= trims(on)
    seq, hops = _new_hops(roofing_hat["off"], both)
    for k, path, direct in hops:
        assert _hop_hidden(seq, k, path, direct), f"both: hop {k} shows"
