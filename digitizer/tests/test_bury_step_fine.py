"""`cfg.extra["bury_step_fine"]` (built OFF 2026-11-06): `cut_every_jump`'s
pass samples a hop's thread every `_BURY_STEP_FINE_MM` (0.01 mm) instead of
`_BURY_STEP_MM` (0.1), for the hop it buries under later thread and the
hop it walks on sewn thread alike. Nothing else moves:
`trim_bury_under_later`'s own pass keeps the coarse step, and OFF is
byte-identical.

The regression is the one card v8 found (`sewout-card-v8-2026-11-01`): a
sewn hop the 0.1 mm samples accept because every one of them lands on
thread, while between two of them the thread's edge dips off the cover --
the browser twin's oracle found the same at 0.015 mm on a seventh of the
font library, and the Python side's at 0.029 mm on one Drone hop (one the
pass BURIED, measured 2026-11-06 with `tools/float_census.py`; the walk
half alone would not have reached it). The fixture here is that blind spot
built by hand: fill rows 0.42 mm apart, so the cover's gaps along the hop's
edge are 0.02 mm wide and fall between the 0.1 mm samples (0.02 mm clear
of each) while the 0.01 mm samples land in them (0.01 mm past the thread).
`tools/jump_walk_oracle.py`, the raster oracle that shares no code with the
pass, reads the coarse walk 0.05 mm off the thread from the DST bytes and
the fine arm's cut clean.
"""
from __future__ import annotations

import copy
import math

import pytest

from digitizer_core import stage7_sequence, stitches
from digitizer_core.stage7_sequence import _BURY_STEP_FINE_MM, _BURY_STEP_MM, _cut_or_bury_jumps
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun

from .test_cut_every_jump import _near_bars
from .test_trim_bury_under_later import _md5

PITCH = 0.42       # rows this far apart leave 0.02 mm of the hop's edge uncovered between them
HOP = ((0.0, 0.0), (2.0, 0.0))


def _rows(pitch=PITCH, offset=0.0, x0=-0.8, x1=2.8, y0=-1.5, y1=1.8, shape="C"):
    """Vertical fill rows every `pitch` from `offset`, one run, no lift of
    its own: the only needle-up move under test is the hop."""
    xs = []
    x = offset - pitch * math.ceil((offset - x0) / pitch)
    while x <= x1:
        if x >= x0:
            xs.append(round(x, 4))
        x += pitch
    pts = []
    for i, x in enumerate(xs):
        pts += [(x, y0), (x, y1)] if i % 2 == 0 else [(x, y1), (x, y0)]
    return [StitchRun(points=pts, kind=stitches.FILL, jump=True, trim=True, shape_id=shape)]


def _hop():
    a = StitchRun(points=[(-1.0, 0.0), HOP[0]], kind=stitches.FILL, shape_id="A")
    b = StitchRun(points=[HOP[1], (3.0, 0.0)], kind=stitches.FILL, jump=True, shape_id="B")
    return a, b


def _block(thread, runs):
    return StitchBlock(thread_index=thread, thread_number=f"{1000 + thread}",
                       rgb=(thread, thread, thread), runs=runs)


def _rows_first():
    """The rows in an EARLIER block: nothing later buries the hop, so the
    walk is the only way it is sewn down."""
    a, b = _hop()
    return [_block(1, _rows()), _block(0, [a, b])]


def _plan(blocks):
    return StitchPlan(blocks=blocks, palette=[], warnings=[])


def test_the_coarse_step_walks_the_hop_and_the_fine_step_cuts_it():
    coarse, fine = _rows_first(), _rows_first()
    assert _cut_or_bury_jumps(coarse, None, _BURY_STEP_MM) == (0, 1, 0)
    assert _cut_or_bury_jumps(fine, None, _BURY_STEP_FINE_MM) == (0, 0, 1)
    assert not coarse[1].runs[1].jump and not coarse[1].runs[1].trim
    assert fine[1].runs[1].trim and fine[1].runs[1].jump


def test_the_default_step_is_the_coarse_one():
    blocks = _rows_first()
    assert _cut_or_bury_jumps(blocks) == (0, 1, 0)


def test_the_oracle_reads_the_coarse_walk_off_thread_and_the_fine_arm_clean():
    """The DST oracle (0.01 mm cells, no code shared with the walk) on the
    OFF file beside each ON file."""
    from tools import jump_walk_oracle as oracle
    off = _rows_first()
    coarse, fine = copy.deepcopy(off), copy.deepcopy(off)
    _cut_or_bury_jumps(coarse, None, _BURY_STEP_MM)
    _cut_or_bury_jumps(fine, None, _BURY_STEP_FINE_MM)
    vc = oracle.judge(_plan(copy.deepcopy(off)), _plan(coarse), "coarse")
    vf = oracle.judge(_plan(copy.deepcopy(off)), _plan(fine), "fine")
    assert vc["walked_segments"] == 1 and vc["bare_walked_segments"] == 1
    assert vc["worst_off_thread_mm"] >= 0.04, vc
    assert vf["walked_segments"] == 0 and vf["bare_segments"] == 0, vf
    assert vf["on_uncut_moves"] == 0 and vc["on_uncut_moves"] == 0


def test_the_pass_buries_at_the_fine_step_too_but_trim_bury_under_later_keeps_the_coarse_one():
    """The same rows sewn AFTER the hop in its own block. The pass's bury
    half: later thread buries the hop at 0.1 and refuses it at 0.01 (the
    Drone hop card v8 flagged was one the pass BURIED, measured 2026-11-06,
    so the fine step has to reach this half), and the walk half refuses it
    too, so it is cut. `trim_bury_under_later`'s own pass
    (`_bury_trims_under_later`) takes no step and still buries the same hop
    when it arrives cut: the flag never reaches it."""
    from digitizer_core.stage7_sequence import _bury_trims_under_later
    a, b = _hop()
    assert _cut_or_bury_jumps([_block(0, [a, b] + _rows())], None, _BURY_STEP_MM) == (1, 0, 0)
    a, b = _hop()
    assert _cut_or_bury_jumps([_block(0, [a, b] + _rows())], None, _BURY_STEP_FINE_MM) == (0, 0, 1)
    a, b = _hop()
    b.trim = True
    assert _bury_trims_under_later([_block(0, [a, b] + _rows())]) == 1
    assert not b.trim and not b.jump


def test_a_fine_walk_still_walks_where_the_thread_is_whole():
    """Rows 0.4 mm apart leave no gap at all: the fine step walks what the
    coarse one walks. The flag refuses only what the oracle would flag."""
    a, b = _hop()
    blocks = [_block(1, _rows(pitch=0.4)), _block(0, [a, b])]
    assert _cut_or_bury_jumps(blocks, None, _BURY_STEP_FINE_MM) == (0, 1, 0)


# --- the flag reaches the pass, and only with cut_every_jump ON -------------

def test_the_flag_hands_the_fine_step_to_the_pass(monkeypatch):
    seen = []
    real = stage7_sequence._cut_or_bury_jumps

    def spy(blocks, small_letters=None, step=_BURY_STEP_MM):
        seen.append(step)
        return real(blocks, small_letters, step)
    monkeypatch.setattr(stage7_sequence, "_cut_or_bury_jumps", spy)
    _near_bars(cut_every_jump=True)
    _near_bars(cut_every_jump=True, extra={"bury_step_fine": True})
    assert seen == [_BURY_STEP_MM, _BURY_STEP_FINE_MM]


def test_the_flag_alone_changes_nothing_with_cut_every_jump_off(monkeypatch):
    """OFF stays OFF: with `cut_every_jump` off the flag is never read and
    the plan is byte-identical (the OFF md5s against main are pinned in
    `test_cut_every_jump.test_off_is_byte_identical_to_base`)."""
    def boom(*_a, **_k):
        raise AssertionError("cut_every_jump code reached with the flag off")
    monkeypatch.setattr(stage7_sequence, "_cut_or_bury_jumps", boom)
    assert _md5(_near_bars(extra={"bury_step_fine": True})) == _md5(_near_bars())


def test_cut_every_jump_step_mm_reads_the_flag():
    from digitizer_core import PipelineConfig
    from digitizer_core.stage7_sequence import cut_every_jump_step_mm
    assert cut_every_jump_step_mm(PipelineConfig()) == _BURY_STEP_MM
    assert cut_every_jump_step_mm(PipelineConfig(extra={"bury_step_fine": False})) == _BURY_STEP_MM
    assert cut_every_jump_step_mm(PipelineConfig(extra={"bury_step_fine": True})) == _BURY_STEP_FINE_MM
    assert cut_every_jump_step_mm(object()) == _BURY_STEP_MM, "a stand-in config with no extra"


@pytest.mark.parametrize("layer", [None, 1])
def test_with_the_flag_no_needle_up_move_is_left_uncut_either(layer):
    from .test_cut_every_jump import _uncut
    assert _uncut(_near_bars(bridge_layer=layer, cut_every_jump=True, extra={"bury_step_fine": True})) == 0
