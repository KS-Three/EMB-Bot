"""`cfg.tie_in_off` (2026-10-22, default OFF, a gate-1 CANDIDATE): no lock at
the start of a run. The pro locks 1 of 68 run starts (settings-vs-pro row 22);
`apply_ties` already locks only at cuts. Lengths are asserted in output
millimetres, never pixels."""
import math

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.stitches import StitchBlock, StitchRun


def _two_runs():
    # Run 1 is the block's first (a cut: colour change); run 2 follows a trim.
    r1 = StitchRun(points=[(0.0, 0.0), (3.0, 0.0), (6.0, 0.0)])
    r2 = StitchRun(points=[(20.0, 0.0), (23.0, 0.0), (26.0, 0.0)], jump=True, trim=True)
    return StitchBlock(thread_index=0, thread_number="1", rgb=(0, 0, 0), runs=[r1, r2])


def _tied():
    b = _two_runs()
    stitches.apply_ties(b.runs)
    return b


def test_default_off():
    assert PipelineConfig().tie_in_off is False


def test_off_locks_both_starts_and_both_ends():
    b = _tied()
    for r, x0 in zip(b.runs, (0.0, 20.0)):
        assert r.tie_in_pts == 4
        assert r.points[0] == (x0, 0.0) and r.points[2] == (x0, 0.0)
        leg = math.dist(r.points[0], r.points[1])
        assert abs(leg - machine.TIE_STITCH_MM) < 1e-9      # mm, not px


def test_on_strips_tie_ins_keeps_tie_offs():
    b = _tied()
    n_before = b.stitch_count
    removed = stitches.drop_tie_ins([b])
    assert removed == 8 and b.stitch_count == n_before - 8
    r1, r2 = b.runs
    assert r1.points[:3] == [(0.0, 0.0), (3.0, 0.0), (6.0, 0.0)]
    assert r2.points[:3] == [(20.0, 0.0), (23.0, 0.0), (26.0, 0.0)]
    # the end locks (tie-off before the trim, and at the design's end) stay
    for r, x_end in ((r1, 6.0), (r2, 26.0)):
        tail = r.points[-4:]
        assert tail[-1] == (x_end, 0.0) and tail[-3] == (x_end, 0.0)
        assert abs(math.dist(tail[-1], tail[-2]) - machine.TIE_STITCH_MM) < 1e-9


def test_bean_retrace_opening_is_not_stripped():
    # A three-pass bean opens p0 p1 p0 p1 on its own; it carries no tie-in
    # and must come through untouched.
    pts = [(0.0, 0.0), (0.7, 0.0), (0.0, 0.0), (0.7, 0.0), (1.4, 0.0)]
    b = StitchBlock(thread_index=0, thread_number="1", rgb=(0, 0, 0),
                    runs=[StitchRun(points=list(pts))])
    assert stitches.drop_tie_ins([b]) == 0
    assert b.runs[0].points == pts


def test_uncut_run_never_gets_a_tie_in():
    b = _two_runs()
    b.runs[1].trim = False                      # a float, not a cut
    stitches.apply_ties(b.runs)
    assert b.runs[1].tie_in_pts == 0
