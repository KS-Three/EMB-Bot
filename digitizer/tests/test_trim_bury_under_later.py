"""`cfg.trim_bury_under_later` (built OFF 2026-10-21): a cut hop is sewn
needle-down only where thread sewn LATER covers the travel's whole width.

The trim-economy study (`docs/trim-economy-2026-10-21.md`) read every trim
in the pro's DST and in ours over ten paired jobs: the pro cut 9 hops that
later thread covers, we cut 43. This file pins the one habit the flag
copies, and the two ways it could show a float, which it must never do:
travel on bare fabric, and travel on top of thread already sewn.

The load-bearing test is `test_no_buried_travel_lies_outside_later_thread`,
which re-measures every travel run the flag added against the real stitches
sewn after it, rebuilt here rather than taken from stage 7.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import replace

import pytest
from shapely.geometry import LineString, Polygon
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, fabric_for_garment, machine, stitches
from digitizer_core import stage7_sequence
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import _bury_trims_under_later, sequence
from digitizer_core.stitches import StitchBlock, StitchRun

from .conftest import PLAN_CFG_KW

FABRIC = fabric_for_garment(PLAN_CFG_KW["garment_id"])   # trims at 3.0 mm
HALF = machine.COVERAGE_THREAD_W_MM / 2.0


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


def _two_bars(bridge_layer=None, **kw):
    """Two same-colour bars 6 mm apart (twice the trim distance), with an
    optional other-colour bridge over the gap, sewn before (layer -1 -> 0
    and the bars move to 1) or after (layer 1) the bars."""
    bars_layer = 1 if bridge_layer == 0 else 0
    regions = [_region(_bar(0, 10), bars_layer, "Sleft", 0),
               _region(_bar(16, 26), bars_layer, "Sright", 0)]
    if bridge_layer is not None:
        regions.append(_region(_bar(10, 16), bridge_layer, "Sbridge", 1))
    return _plan(regions, **kw)


def _crossing(blocks):
    for b in blocks:
        runs = b.runs
        for i, run in enumerate(runs):
            if i and {run.shape_id, runs[i - 1].shape_id} == {"Sleft", "Sright"}:
                return run
    raise AssertionError("the plan never got from one bar to the other")


def _md5(blocks) -> str:
    rows = [[b.thread_index, [[round(x, 4), round(y, 4), r.kind, bool(r.jump), bool(r.trim)]
                              for r in b.runs for x, y in r.points]] for b in blocks]
    return hashlib.md5(json.dumps(rows).encode()).hexdigest()


def _thread(seq, ks, near):
    """The footprint of every non-travel run in `ks` that reaches `near`:
    each centreline buffered to the thread's half width. Local on purpose --
    a whole-plan union of thousands of capsules is slow and GEOS loses
    precision on it."""
    feet = []
    for j in ks:
        r = seq[j]
        pts = list(r.points)
        if j > 0 and not r.jump and seq[j - 1].points:
            pts = [seq[j - 1].points[-1]] + pts
        if r.kind != stitches.TRAVEL and len(pts) >= 2:
            line = LineString(pts)
            if line.intersects(near):
                feet.append(line.buffer(HALF))
    return unary_union(feet) if feet else None


def _travel_is_hidden(seq, k, path) -> bool:
    """The travel's whole thread lies under thread sewn after it; within one
    thread width of the two penetrations it starts and ends on, under any
    thread (the previous run's last stitch arrives there). Nothing bare.

    The engine samples every `_BURY_STEP_MM`; a slit in the later thread
    narrower than that (a hairline between two fanned satin crosses, 0.002
    mm² on Becker) can pass it. So this asks for no uncovered gap wider than
    half a step, which is what the sampling promises, and no more."""
    body = LineString(path).buffer(HALF)
    near = body.buffer(machine.COVERAGE_THREAD_W_MM)
    later = _thread(seq, range(k + 1, len(seq)), near)
    every = _thread(seq, range(len(seq)), near)
    if later is None:
        return False
    ends = (LineString(path[:2]).interpolate(0).buffer(machine.COVERAGE_THREAD_W_MM)
            .union(LineString(path[-2:]).interpolate(1, normalized=True)
                   .buffer(machine.COVERAGE_THREAD_W_MM)))
    allowed = later.union(every.intersection(ends))
    bare = body.difference(allowed)
    return bare.buffer(-stage7_sequence._BURY_STEP_MM / 4.0).is_empty


def _new_travel(off_blocks, on_blocks):
    """(flat ON sew order, indices of the travel runs ON added)."""
    off_keys = {tuple(map(tuple, r.points)) for b in off_blocks for r in b.runs
                if r.kind == stitches.TRAVEL}
    seq = [r for b in on_blocks for r in b.runs]
    return seq, [k for k, r in enumerate(seq) if r.kind == stitches.TRAVEL
                 and tuple(map(tuple, r.points)) not in off_keys]


# --- OFF: byte-identical, and the new code is never reached ----------------

# Captured on the base commit (2e873933), before the flag existed.
OFF_MD5 = {"bars": "2a069a432c3ef7831b575cf0dd74d584",
           "later": "4c2b546580cbb66c6c60675fd91ec6fd",
           "earlier": "3f972a1552901bbdc2bf625e8b135d08"}


def test_off_never_reaches_the_new_code(monkeypatch):
    def boom(*_a, **_k):
        raise AssertionError("trim_bury_under_later code reached with the flag off")
    monkeypatch.setattr(stage7_sequence, "_bury_trims_under_later", boom)
    _two_bars(bridge_layer=1)
    _two_bars()


@pytest.mark.parametrize("case,layer", [("bars", None), ("later", 1), ("earlier", 0)])
def test_off_is_byte_identical_to_base(case, layer):
    assert _md5(_two_bars(bridge_layer=layer)) == OFF_MD5[case]


# --- ON: the one habit -------------------------------------------------------

def test_a_hop_later_thread_buries_is_sewn_not_cut():
    off = _crossing(_two_bars(bridge_layer=1))
    assert off.trim, "precondition: with the flag off this hop is cut"
    blocks = _two_bars(bridge_layer=1, trim_bury_under_later=True)
    run = _crossing(blocks)
    assert run.kind == stitches.TRAVEL and not run.trim and not run.jump


def test_a_hop_over_bare_fabric_is_still_cut():
    run = _crossing(_two_bars(trim_bury_under_later=True))
    assert run.trim, "nothing covers the gap: the cut stays"


def test_a_hop_over_thread_already_sewn_is_still_cut():
    """The bridge sews FIRST, so travel across it would lie on top of
    finished thread -- what `chain_links` allows and this flag does not."""
    run = _crossing(_two_bars(bridge_layer=0, trim_bury_under_later=True))
    assert run.trim


def test_a_colour_change_is_never_buried():
    blocks = _two_bars(bridge_layer=1, trim_bury_under_later=True)
    assert all(b.runs[0].trim for b in blocks)


def test_a_gap_past_the_chaining_knee_is_still_cut():
    a = StitchRun(points=[(0.0, 0.0), (1.0, 0.0)], kind=stitches.FILL, shape_id="A")
    far = machine.LINK_MAX_GAP_MM + 5.0
    b = StitchRun(points=[(far, 0.0), (far + 1.0, 0.0)], kind=stitches.FILL,
                  jump=True, trim=True, shape_id="B")
    # A later fill that covers the whole gap, row by row.
    rows = [StitchRun(points=[(-1.0, y), (far + 2.0, y)], kind=stitches.FILL, shape_id="C")
            for y in [i * 0.15 - 3.0 for i in range(41)]]
    block = StitchBlock(thread_index=0, thread_number="1000", rgb=(0, 0, 0),
                        runs=[a, b] + rows)
    assert _bury_trims_under_later([block]) == 0
    assert b.trim


def test_a_route_bends_under_later_thread_rather_than_cutting():
    """Later thread covers an L round the gap, not the straight line."""
    a = StitchRun(points=[(-1.0, 0.0), (0.0, 0.0)], kind=stitches.FILL, shape_id="A")
    b = StitchRun(points=[(8.0, 0.0), (9.0, 0.0)], kind=stitches.FILL,
                  jump=True, trim=True, shape_id="B")
    # An up-across-down band, 1.5 mm wide, rows 0.15 mm apart. Each row is
    # its own needle-up run so no connector thread crosses the gap.
    rows = []
    for i in range(11):
        o = i * 0.15 - 0.75
        for pts in ([(o, -0.5), (o, 6.0)], [(-0.75, 5.25 + o), (8.75, 5.25 + o)],
                    [(8.0 + o, 6.0), (8.0 + o, -0.5)]):
            rows.append(StitchRun(points=pts, kind=stitches.FILL, jump=True, shape_id="C"))
    block = StitchBlock(thread_index=0, thread_number="1000", rgb=(0, 0, 0),
                        runs=[a, b] + rows)
    assert _bury_trims_under_later([block]) == 1
    travel = block.runs[1]
    assert travel.kind == stitches.TRAVEL and not b.trim
    assert max(y for _x, y in travel.points) > 4.0, "the route went round, under the band"


# --- the invariant: no buried travel shows -----------------------------------

@pytest.mark.parametrize("layer", [1, None, 0])
def test_no_buried_travel_lies_outside_later_thread(layer):
    off = _two_bars(bridge_layer=layer)
    on = _two_bars(bridge_layer=layer, trim_bury_under_later=True)
    seq, new = _new_travel(off, on)
    for k in new:
        r = seq[k]
        path = [seq[k - 1].points[-1]] + list(r.points) + [seq[k + 1].points[0]]
        assert _travel_is_hidden(seq, k, path), f"travel at {k} shows"
        assert math.dist(path[0], path[-1]) <= machine.LINK_MAX_GAP_MM


@pytest.fixture(scope="module")
def becker_hat():
    """The committed customer artwork at the pro's hat width (101.9 mm,
    `beckers logo hat.DST`), through the Studio's own request -- the path
    `tools/pro_pair.py` runs and the study measured -- planned both ways
    from one generation. (-> off blocks, on blocks)"""
    from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches
    from digitizer_service.app import _decode, _parse_config
    from tools.pro_pair import request
    from .conftest import TESTDATA
    data = (TESTDATA / "becker_marine_logo.png").read_bytes()
    conf = PipelineConfig(**_parse_config(json.dumps(request(101.9, "hat_front"))))
    gen = build_generation(_decode(data), conf, exif_source=data)
    out = []
    for on in (False, True):
        c = replace(conf, trim_bury_under_later=on)
        out.append(plan_stitches(finish_generation(gen.fork(), c), c).blocks)
    return out


def test_no_buried_travel_shows_on_committed_artwork(becker_hat):
    """The same invariant on real artwork, over the finished plan (ties in),
    so a tie or a later pass that moved thread would show here."""
    off, on = becker_hat
    seq, new = _new_travel(off, on)
    trims = lambda blocks: sum(r.trim for b in blocks for r in b.runs)
    assert new, "nothing buried: the fixture no longer exercises the flag"
    assert trims(on) < trims(off)
    for k in new:
        path = [seq[k - 1].points[-1]] + list(seq[k].points) + [seq[k + 1].points[0]]
        assert _travel_is_hidden(seq, k, path), f"becker: travel {k} shows"


def test_a_buried_hop_drops_its_locks_and_every_left_cut_keeps_them():
    """The ties run after the pass, so a hop made travel carries no lock and
    a hop still cut is locked on both sides, as `apply_ties` always does."""
    blocks = _two_bars(bridge_layer=1, trim_bury_under_later=True)
    run = _crossing(blocks)
    assert run.kind == stitches.TRAVEL
    # a lock is a back-and-forth at the run's head: no travel run has one
    assert len(run.points) == len(set(run.points))
