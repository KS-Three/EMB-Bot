"""`cfg.extra["split_long_inshape_stitches"]` (built OFF 2026-11-07).

`stitch_shape` hands back its first run needle-down: the step INTO a shape
is the caller's. Two callers in `stage7_sequence.stitch_one` sew one shape
as several pieces and concatenate the calls -- `border_from_outline`'s body
pieces and `enclosed_white_keyline`'s, both off `keyline_rest` -- so the
step from one piece's last stitch to the next piece's first is a plain
needle-down stitch nothing measured. `docs/float-census-2026-11-06.md`
found it on all five Becker pairs: 13.8-16.7 mm into the next piece's
underlay and 34.4-37.5 mm into the next one's fill (S92f2350b, Sd86ce3cb,
S118e45fc), past `machine.MAX_STITCH_MM`, so the DST writer encodes each
as jump records and the machine flies it uncut. ON, `join_piece` splits
that step with `stitches.split_long_moves` at the machine ceiling (no new
constant), as a TRAVEL run of the inner points: the thread lies on the
same line, tacked down, and no cut is added. OFF is never read.

The fixtures are the two callers' own tests': `test_border_from_outline`'s
30 x 12 mm face in a keyline drawn 3.2 mm (and 4 mm) thick, whose rest past
the loop is one strip -- cut in two here, 24 mm apart, as Becker's pieces
are disjoint -- and `test_enclosed_white_keyline`'s band with a tab at each
end past the loops' reach: two pieces 37 mm apart, no patching.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import Polygon, box

from digitizer_core import machine, stage7_sequence, stitches
from digitizer_core.stage7_sequence import join_piece, split_long_inshape
from digitizer_core.stitches import StitchRun

from .test_border_from_outline import FACE, FAT, KEY, THICK, _md5, _plan

FLAG = "split_long_inshape_stitches"


def _steps(runs):
    """Every needle-down step of `runs`, the one INTO a non-jump run
    included (what the DST writer sees). -> [(length, run index)]"""
    out, last = [], None
    for i, r in enumerate(runs):
        pts = list(r.points)
        if last is not None and not r.jump and pts:
            pts = [last] + pts
        out += [(math.dist(a, b), i) for a, b in zip(pts, pts[1:])]
        if r.points:
            last = r.points[-1]
    return out


def _too_long(runs):
    return [d for d, _i in _steps(runs) if d > machine.MAX_STITCH_MM + stitches.SPLIT_TOLERANCE_MM]


def _on(outline, body, **kw):
    return _plan(outline, body, border_from_outline=True, extra={FLAG: True}, **kw)


# ------------------------------------------------------------------ the flag
def test_flag_reads_off_by_default():
    from digitizer_core import PipelineConfig
    assert split_long_inshape(PipelineConfig()) is False
    assert split_long_inshape(PipelineConfig(extra={FLAG: True})) is True
    assert split_long_inshape(None) is False


@pytest.mark.parametrize("ring", [THICK, FAT, KEY], ids=["thick", "fat", "key"])
def test_off_is_byte_identical_with_the_key_false_or_absent(ring):
    absent = _plan(ring, FACE, border_from_outline=True)
    false = _plan(ring, FACE, border_from_outline=True, extra={FLAG: False})
    assert _md5(false) == _md5(absent)


# ------------------------------------------------------------------ join_piece
def _run(pts, kind=stitches.FILL, **kw):
    return StitchRun(points=list(pts), kind=kind, shape_id="S", **kw)


def test_join_splits_a_long_step_into_a_travel_run_at_the_ceiling():
    prev = [_run([(0.0, 0.0), (1.0, 0.0)])]
    nxt = [_run([(38.45, 0.0), (39.0, 0.0)], kind=stitches.UNDERLAY, shade_thread_index=3),
           _run([(39.0, 1.0), (40.0, 1.0)])]
    got = join_piece(prev, nxt, "S")
    assert got[1:] == nxt                       # the piece itself is untouched
    t = got[0]
    assert t.kind == stitches.TRAVEL and not t.jump and not t.trim
    assert t.shape_id == "S" and t.shade_thread_index == 3
    chain = [prev[-1].points[-1]] + t.points + [nxt[0].points[0]]
    steps = [math.dist(a, b) for a, b in zip(chain, chain[1:])]
    assert max(steps) <= machine.MAX_STITCH_MM
    assert len(steps) == math.ceil(37.45 / machine.MAX_STITCH_MM)   # 4 equal steps
    assert max(steps) - min(steps) < 1e-9
    for p in t.points:                          # on the straight line the machine flew
        assert abs(p[1]) < 1e-12 and 1.0 < p[0] < 38.45


@pytest.mark.parametrize("case", ["fits", "at_ceiling", "jump", "no_prev", "no_next"])
def test_join_leaves_everything_else_alone(case):
    prev = [_run([(0.0, 0.0), (1.0, 0.0)])]
    far = 1.0 + 20.0
    nxt = {
        "fits": [_run([(1.0 + 12.0, 0.0), (14.0, 0.0)])],
        "at_ceiling": [_run([(1.0 + machine.MAX_STITCH_MM, 0.0), (20.0, 0.0)])],
        "jump": [_run([(far, 0.0), (far + 1, 0.0)], jump=True, trim=True)],
        "no_prev": [_run([(far, 0.0), (far + 1, 0.0)])],
        "no_next": [],
    }[case]
    got = join_piece([] if case == "no_prev" else prev, nxt, "S")
    assert got == nxt


# ------------------------------------------------------------------ in the sequencer
@pytest.fixture
def two_pieces(monkeypatch):
    """`keyline_rest` as Becker's outline gives it: disjoint pieces. THICK's
    and FAT's rest is one strip round the face, so it is cut in two here, at
    x = -12 and +12 (24 mm apart, the face's own width between them)."""
    orig = stage7_sequence.keyline_rest

    def split_rest(*a, **k):
        out = []
        for piece in orig(*a, **k):
            for half in (box(-100, -100, -12, 100), box(12, -100, 100, 100)):
                g = piece.intersection(half)
                out += [p for p in getattr(g, "geoms", [g]) if p.area > 0.5]
        return out

    monkeypatch.setattr(stage7_sequence, "keyline_rest", split_rest)


def _check_split(off, on, sid):
    # the defect, reproduced: a needle-down step past the ceiling between two
    # fill pieces of one shape, with no lift on it
    long_off = [(d, i) for d, i in _steps(off) if d > machine.MAX_STITCH_MM]
    assert long_off, "fixture no longer has a long step between pieces"
    for _d, i in long_off:
        assert off[i].shape_id == sid and off[i - 1].shape_id == sid
        assert off[i].kind == stitches.FILL and not off[i].jump
    assert _too_long(on) == []
    # ON is OFF with one TRAVEL run in front of each such piece, nothing else
    added = [r for r in on if r not in off]
    assert len(added) == len(long_off)
    assert all(r.kind == stitches.TRAVEL and r.shape_id == sid and not r.jump and not r.trim
               for r in added)
    assert _md5([r for r in on if r not in added]) == _md5(off)
    # no lift and no cut added
    assert sum(r.jump for r in on) == sum(r.jump for r in off)
    assert sum(r.trim for r in on) == sum(r.trim for r in off)
    return long_off


@pytest.mark.parametrize("ring", [THICK, FAT], ids=["thick", "fat"])
def test_border_from_outline_pieces_are_joined_under_the_ceiling(two_pieces, ring):
    off = _plan(ring, FACE, border_from_outline=True)
    on = _on(ring, FACE)
    long_off = _check_split(off, on, "Souter")
    assert [round(d) for d, _i in long_off] == [24]


def test_enclosed_white_keyline_pieces_are_joined_under_the_ceiling():
    # `test_enclosed_white_keyline`'s two tabs past the loops' reach: two
    # `keyline_rest` pieces 37 mm apart, filled first, under the loops
    from .test_enclosed_white_keyline import LEFT, OUTER, RIGHT
    from .test_enclosed_white_keyline import _plan as kplan
    two = Polygon(OUTER.union(Polygon([(17, -1.5), (20, -1.5), (20, 1.5), (17, 1.5)]))
                  .union(Polygon([(-20, -1.5), (-17, -1.5), (-17, 1.5), (-20, 1.5)])).exterior,
                  [LEFT.exterior, RIGHT.exterior])
    off = kplan(two, enclosed_white_keyline=True)
    on = kplan(two, enclosed_white_keyline=True, extra={FLAG: True})
    _check_split(off, on, "Sband")


@pytest.mark.parametrize("ring", [THICK, FAT, KEY], ids=["thick", "fat", "key"])
def test_on_a_one_piece_outline_changes_nothing(ring):
    # unsplit, THICK's and FAT's rest is one strip and KEY's loop reaches all
    # of it: no second piece, no join
    assert _md5(_on(ring, FACE)) == _md5(_plan(ring, FACE, border_from_outline=True))
