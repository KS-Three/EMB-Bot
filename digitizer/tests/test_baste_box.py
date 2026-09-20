"""The basting box (`cfg.baste_box`, default OFF).

A rectangle of long, loose running stitches sewn OUTSIDE the design before any
artwork, so the operator can stop the machine after ten seconds and see whether
the garment is hooped straight — instead of finding out after eighteen thousand
stitches. It is picked out with tweezers afterwards, which is why the stitch is
deliberately long.

Machine-physics playbook law 25 names it ("optional basting box on knits") and
rates it Desk-safe. It was never built: zero matches for baste/basting anywhere
in the repo before this file.

**Three engineering choices, none of them Kent's to make, all stated here so
they are not mistaken for accidents:**

- **It sews in the FIRST ARTWORK THREAD**, prepended into that block rather
  than emitted as a block of its own. A block boundary is a colour change, and
  on a single head that is a machine stop and a re-thread — a basting box that
  costs the operator a stop has taken more than it gave. Same thread, one
  block, no stop.
- **It is inserted AFTER the silhouette cap and the detail layer are planned**,
  so it cannot join `_sewn_linear_cover`. Basting is removed from the finished
  garment; if it counted as cover, it would suppress the very edge cap it sits
  outside of, and the design would ship missing a finish because of thread that
  is not there any more.
- **The artwork lifts away from it.** The first artwork run gets `jump` and
  `trim` so the needle does not drag from the box into the design.

Default OFF by Kent's call (2026-09-20): it adds stitches nobody asked for, and
this repo's standing pattern for that is a control the user turns on.
"""
from __future__ import annotations

from digitizer_core import PipelineConfig, digitize, export, machine
from tests.conftest import TESTDATA, cfg

FIXTURE = TESTDATA / "logo_whitebg.png"


def _plan(**kw):
    return digitize(FIXTURE, cfg(garment_id="left_chest", **kw))[1]


def _baste_runs(plan):
    return [r for _b, r in plan.iter_runs() if r.shape_id == "__baste_box__"]


def _artwork_points(plan):
    return [p for _b, r in plan.iter_runs() if r.shape_id != "__baste_box__"
            for p in r.points]


def test_baste_box_defaults_off():
    """Kent's 2026-09-20 call, recorded as a failing test the day it changes."""
    assert PipelineConfig().baste_box is False


def test_off_is_byte_identical():
    """The feature existing must not move a stitch of a design that never asked
    for it. Pinned on exported DST bytes, not a stitch count."""
    a = export.export_dst(_plan())
    b = export.export_dst(_plan(baste_box=False))
    assert a == b
    assert not _baste_runs(_plan())


def test_the_box_sews_before_any_artwork():
    """The whole point: it is the first thread down, so the operator can stop
    and look before committing the job."""
    plan = _plan(baste_box=True)
    first = next(r for _b, r in plan.iter_runs())
    assert first.shape_id == "__baste_box__"


def test_the_box_encloses_the_artwork_with_a_margin():
    plan = _plan(baste_box=True)
    box = [p for r in _baste_runs(plan) for p in r.points]
    assert box, "no basting runs emitted"
    art = _artwork_points(plan)
    bx0, bx1 = min(p[0] for p in box), max(p[0] for p in box)
    by0, by1 = min(p[1] for p in box), max(p[1] for p in box)
    ax0, ax1 = min(p[0] for p in art), max(p[0] for p in art)
    ay0, ay1 = min(p[1] for p in art), max(p[1] for p in art)
    # Outside on every side, by about the margin. Loose bounds: the point is
    # that it surrounds the work and does not touch it, not a pinned offset.
    assert bx0 < ax0 and by0 < ay0 and bx1 > ax1 and by1 > ay1
    for gap in (ax0 - bx0, ay0 - by0, bx1 - ax1, by1 - ay1):
        assert machine.BASTE_MARGIN_MM * 0.5 <= gap <= machine.BASTE_MARGIN_MM * 2.0


def test_it_costs_no_extra_colour_stop():
    """A basting box that makes the operator re-thread has taken more than it
    gave. Same block count, same threads, in the same order."""
    off, on = _plan(), _plan(baste_box=True)
    assert len(on.blocks) == len(off.blocks)
    assert [b.thread_number for b in on.blocks] == [b.thread_number for b in off.blocks]


def test_the_artwork_lifts_away_from_the_box():
    """Without this the needle drags from the box straight into the design,
    leaving a line of thread across the garment that basting was supposed to
    stay clear of."""
    plan = _plan(baste_box=True)
    runs = [r for _b, r in plan.iter_runs()]
    first_art = next(i for i, r in enumerate(runs) if r.shape_id != "__baste_box__")
    assert runs[first_art].jump
    assert runs[first_art].trim


def test_the_stitch_is_long_enough_to_pull_out():
    """Basting is removed by hand. A dense ring is a second design to unpick."""
    plan = _plan(baste_box=True)
    gaps = []
    for r in _baste_runs(plan):
        pts = r.points
        for a, b in zip(pts, pts[1:]):
            gaps.append(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5)
    assert gaps, "no basting stitches"
    longest = max(gaps)
    assert longest <= machine.MAX_STITCH_MM, "a stitch the format cannot encode"
    # Long, but not so long the box wanders: the median lands on the constant.
    gaps.sort()
    assert gaps[len(gaps) // 2] >= machine.BASTE_STITCH_MM * 0.75
