"""`cfg.trim_every_jump` (built OFF 2026-10-21): no needle-up move inside a
colour block is left uncut, like the professional's files. A hop no longer
than one run stitch is sewn needle-down; a longer one is cut and locked.

`docs/settings-vs-pro-2026-10-21.md` row 25: the pro's 28 DSTs leave no
needle-up move uncut; ours left 0-168 jumps of 0.5-3.0 mm per job, under
`trim_at_mm`. The load-bearing tests are the DST one (no uncut jump in the
written file, read back record by record with `tools/uncut_jumps.py`) and
the needle-down one (travel the plan sews on purpose stays travel).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import replace

from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, fabric_for_garment, pipeline, stitches
from digitizer_core.export import export_dst
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun, cut_every_jump
from tools.uncut_jumps import moves

from .conftest import PLAN_CFG_KW

FABRIC = fabric_for_garment(PLAN_CFG_KW["garment_id"])   # trims at 3.0 mm
# Points one lock adds to the run it is folded into (`apply_ties`' rule).
TIE = len(stitches.tie_run((0.0, 0.0), (1.0, 0.0)).points) - 1


def _region(poly, layer, name, thread):
    return Region(shape_id=name, polygon=poly, thread_index=thread,
                  thread_number=f"{1000 + thread}", area_mm2=poly.area,
                  meta={"layer": layer, "tier": "fill"})


def _bar(x0, x1, y0=0.0, y1=10.0):
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def _plan(regions, **kw):
    conf = PipelineConfig(**{**PLAN_CFG_KW, **kw})
    planned, _ = resolve_overlaps(regions, FABRIC, conf)
    blocks, _ = sequence(planned, FABRIC, conf)
    return blocks


def _near_bars(**kw):
    """Two same-colour bars 2 mm apart: under the 3.0 mm trim distance, so
    the hop between them is a jump the default leaves uncut."""
    return _plan([_region(_bar(0, 10), 0, "Sleft", 0),
                  _region(_bar(12, 22), 0, "Sright", 0)], **kw)


def _touching_bars(**kw):
    """Two same-colour bars 0.8 mm apart: the hop is a jump under one run
    stitch, the kind Fremont's small text is full of."""
    return _plan([_region(_bar(0, 10), 0, "Sleft", 0),
                  _region(_bar(10.8, 20.8), 0, "Sright", 0)], **kw)


def _bridged_bars(**kw):
    """Two same-colour bars 6 mm apart with another colour sewn LATER over
    the gap: `trim_bury_under_later` sews that hop needle-down."""
    return _plan([_region(_bar(0, 10), 0, "Sleft", 0),
                  _region(_bar(16, 26), 0, "Sright", 0),
                  _region(_bar(10, 16), 1, "Sbridge", 1)], **kw)


def _crossing(blocks):
    for b in blocks:
        for i, run in enumerate(b.runs):
            if i and {run.shape_id, b.runs[i - 1].shape_id} == {"Sleft", "Sright"}:
                return run
    raise AssertionError("the plan never got from one bar to the other")


def _md5(blocks) -> str:
    rows = [[b.thread_index, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                              for r in b.runs for x, y in r.points]] for b in blocks]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _dst(blocks) -> bytes:
    return export_dst(StitchPlan(blocks=blocks, palette=[{} for _ in blocks]))


def _uncut(blocks, tmp_path) -> list[dict]:
    p = tmp_path / "plan.dst"
    p.write_bytes(_dst(blocks))
    return [m for m in moves(p) if m["kind"] == "uncut"]


# --- OFF: byte-identical, and the new code is never reached ----------------

# Captured on the base commit (03ccab4e), before the flag existed.
OFF_MD5 = {"near": "46bede5a3d93e11a2a425893b0881e3a",
           "touching": "74972cc917d55b9d4f93905e465d43a0",
           "bridged": "4c2b546580cbb66c6c60675fd91ec6fd"}


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("trim_every_jump code reached with the flag off")
    monkeypatch.setattr(stitches, "cut_every_jump", boom)
    monkeypatch.setattr(pipeline, "cut_every_jump", boom)
    _near_bars()
    _touching_bars()
    _bridged_bars()


def test_off_is_byte_identical_to_base():
    assert _md5(_near_bars()) == OFF_MD5["near"]
    assert _md5(_touching_bars()) == OFF_MD5["touching"]
    assert _md5(_bridged_bars()) == OFF_MD5["bridged"]


def test_off_leaves_the_short_hop_an_uncut_jump(tmp_path):
    """The defect, reproduced: a 2 mm hop is a jump with no trim."""
    run = _crossing(_near_bars())
    assert run.jump and not run.trim
    assert _uncut(_near_bars(), tmp_path)


# --- ON ---------------------------------------------------------------------

def test_on_cuts_the_short_hop_and_locks_both_sides():
    off = _near_bars()
    on = _near_bars(trim_every_jump=True)
    run_off, run_on = _crossing(off), _crossing(on)
    assert run_on.jump and run_on.trim
    # Locked like every other cut: a tie-in on the run, a tie-off before it.
    assert len(run_on.points) == len(run_off.points) + TIE
    seq_on = [r for b in on for r in b.runs]
    seq_off = [r for b in off for r in b.runs]
    k = seq_on.index(run_on)
    assert len(seq_on[k - 1].points) == len(seq_off[k - 1].points) + TIE


def test_on_writes_no_uncut_jump_to_the_dst(tmp_path):
    assert _uncut(_near_bars(), tmp_path)                       # the control
    assert _uncut(_near_bars(trim_every_jump=True), tmp_path) == []
    on = [m for m in moves(tmp_path / "plan.dst") if m["kind"] == "cut"]
    assert any(1.9 < m["mm"] < 3.0 for m in on)                 # the 2 mm hop, cut


def test_on_keeps_needle_down_travel(tmp_path):
    """A hop the plan sews needle-down on purpose is not a needle-up move:
    with `trim_bury_under_later` burying it, it stays travel."""
    buried = _crossing(_bridged_bars(trim_bury_under_later=True))
    assert not buried.jump and buried.kind == stitches.TRAVEL
    both = _bridged_bars(trim_bury_under_later=True, trim_every_jump=True)
    run = _crossing(both)
    assert not run.jump and not run.trim and run.kind == stitches.TRAVEL
    assert _uncut(both, tmp_path) == []


def test_on_sews_a_hop_under_one_run_stitch_needle_down(tmp_path):
    off, on = _touching_bars(), _touching_bars(trim_every_jump=True)
    run_off, run_on = _crossing(off), _crossing(on)
    assert run_off.jump and not run_off.trim                    # the control
    assert not run_on.jump and not run_on.trim                  # one stitch
    assert run_on.points == run_off.points                      # no lock added
    assert _uncut(on, tmp_path) == []
    # Nothing but the one flag moved: the same points, the same trims.
    flat_off = [p for b in off for r in b.runs for p in r.points]
    flat_on = [p for b in on for r in b.runs for p in r.points]
    assert flat_on == flat_off
    assert sum(r.trim for b in on for r in b.runs) == sum(r.trim for b in off for r in b.runs)


def test_cut_every_jump_on_hand_built_runs():
    def run(x, **kw):
        return StitchRun(points=[(x, 0.0), (x + 2.0, 0.0), (x + 4.0, 0.0)], **kw)
    first = run(0.0, jump=True)                 # a block start: a machine stop
    walk = run(4.0)                             # needle-down: untouched
    near = run(9.5, jump=True)                  # 1.5 mm hop: sewn needle-down
    far = run(16.0, jump=True)                  # 2.5 mm hop: cut
    cut = run(25.0, jump=True, trim=True)       # already cut: untouched
    empty = StitchRun(points=[], jump=True)     # no points: skipped
    edge = run(31.0, jump=True)                 # exactly one run stitch: sewn
    after = run(40.0, jump=True)                # 5 mm: cut
    block = StitchBlock(thread_index=0, thread_number="1000", rgb=(0, 0, 0),
                        runs=[first, walk, near, far, cut, empty, edge, after])
    lens = [len(r.points) for r in block.runs]
    assert cut_every_jump([block]) == (2, 2)
    assert first.jump and not first.trim
    assert not walk.jump and not walk.trim
    assert not near.jump and not near.trim and not edge.jump and not edge.trim
    assert far.jump and far.trim and after.jump and after.trim and cut.trim
    assert not empty.trim
    # Each new cut ties off the run before it and ties itself in; a hop sewn
    # needle-down gains no lock.
    assert [len(r.points) for r in block.runs] == [
        lens[0], lens[1], lens[2] + TIE, lens[3] + TIE, lens[4], 0,
        lens[6] + TIE, lens[7] + TIE]
    # Idempotent: nothing left to resolve.
    assert cut_every_jump([block]) == (0, 0)


def test_flag_defaults_off():
    assert PipelineConfig().trim_every_jump is False
    assert replace(PipelineConfig(), trim_every_jump=True).trim_every_jump is True
