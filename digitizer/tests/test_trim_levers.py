"""The lettering yardstick's trims gap, read and answered (2026-09-19).

Traced MARINE at 80 mm sews 13 trims against the typed word's 3. A per-trim
census (scope-history 2026-09-19) puts the lettering trims across the nine
logos in three buckets: the hop from one letter to the NEXT (the Euler walk
starts nearest the needle and ends wherever the postman pairing leaves it,
so the next letter is a jump over `trim_at`), the walk refusing a
within-letter hop, and the hop from a stroke's underlay to its own column
(cap-extended and, under the stack, run into the node; the underlay is not).

Two levers, one flag each, both BUILT OFF, and lever 1 FLIPPED ON the same
day on Kent's call (lever 2 stays OFF):

* `satin_exit_toward_next` (folded into the code 2026-11-19) -- stage 7 hands the emitter the nearest
  point of the shape it will sew next and the walk picks its (start, end)
  odd-node pair to minimise the entry hop plus the exit hop
  (`_euler_stroke_order(end_near=...)`).
* `cfg.satin_underlay_on_column` -- an open stroke's underlay is built on its
  column's own stations, starts on the web (the raw spine's end) so the walk
  can still reach it, and its last stitch carries the needle to where the
  column enters.

Measured on the fixture (2026-09-19): 13 trims -> 9 with the exit lever
(letter-to-letter 6 -> 3, the typed word's 3) at 1,969 -> 1,953 stitches;
-> 12 with the underlay lever at 2,146; -> 8 with both at 2,132. Pinned as
directions and floors. The pre-flip walk (`end_near=None`) is still what
`_euler_stroke_order` does without an `end_near`, pinned at function level.
"""
from __future__ import annotations

import math

import pytest
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, machine
from tests.conftest import FLIP_2026_10_23  # the 2026-10-23 flips, pinned off: this file prices another flag
from digitizer_core import stage6_satin as s6
from digitizer_core import stitches
from digitizer_core import textcluster as tc
from digitizer_core.pipeline import build_generation, finish_generation, plan_stitches

from .test_stroke_order_euler import FIXTURE, _stroke

pytestmark = pytest.mark.filterwarnings("ignore::DeprecationWarning")


def _run(**kw):
    # And on the skeleton tier, explicitly: `lettering_columns` went ON by
    # default 2026-10-12 (Kent), and the Column lane sews MARINE's letters with
    # its own walk, so the two levers priced here (the skeleton walk's exit and
    # underlay) would price nothing. The lane's own trims are pinned in
    # `tests/test_lettering_columns.py`.
    kw.setdefault("lettering_columns", False)
    # ...and the 2026-10-23 flips (buried hops, no start locks, short-column
    # underlay): every trim count here was read without them.
    for k, v in FLIP_2026_10_23.items():
        kw.setdefault(k, v)
    cfg = PipelineConfig(target_width_mm=80.2, garment_id="left_chest", max_colors=6, **kw)
    gen = build_generation(str(FIXTURE), cfg)
    result = finish_generation(gen.fork(), cfg)
    # `trim_bury_under_later` is folded into the code (2026-11-20, B5); this file prices the trims
    # on the engine before it, so its pass is stubbed out
    from unittest import mock
    from digitizer_core import stage7_sequence
    with mock.patch.object(stage7_sequence, "_bury_trims_under_later", return_value=0):
        return result, plan_stitches(result, cfg)


def _points(plan):
    return [(r.kind, r.jump, r.trim, r.points) for _b, r in plan.iter_runs()]


def _trims_by_cause(result, plan) -> dict[str, int]:
    """Lettering trims: 'letter-to-shape' (the run before is another shape's),
    or 'kind->kind' within one letter."""
    letters = {r.shape_id for g in tc._lettering_groups(result.regions) for r in g}
    runs = [run for _b, run in plan.iter_runs()]
    out: dict[str, int] = {}
    for i, cur in enumerate(runs):
        if not cur.trim or i == 0 or cur.shape_id not in letters:
            continue
        prev = runs[i - 1]
        key = "letter-to-shape" if prev.shape_id != cur.shape_id else f"{prev.kind}->{cur.kind}"
        out[key] = out.get(key, 0) + 1
    return out


@pytest.fixture(scope="module")
def exit_on():
    """The shipped walk (the exit lever folded in), the baseline the underlay lever is priced against."""
    return _run()


@pytest.fixture(scope="module")
def both_on():
    return _run(satin_underlay_on_column=True)


# --- the flags -----------------------------------------------------------------

def test_lever_two_is_off_by_default():
    """Lever one shipped ON the day it was built (Kent's call over the numbers
    in the module docstring) and is folded into the code; lever two is still
    a flag, OFF."""
    assert PipelineConfig().satin_underlay_on_column is False


# --- the exit lever: the walk ends facing the next letter ------------------------

def _h_strokes():
    """An H: two stems and a bar. Four dead ends and two junctions are odd, so
    the walk has a choice of ends."""
    left = _stroke((0, 0), (0, 5), (0, 10))
    right = _stroke((10, 0), (10, 5), (10, 10))
    bar = _stroke((0, 5), (5, 5), (10, 5), free_start=False, free_end=False)
    return [left, right, bar]


def _walk_end(strokes, order, entry):
    k = order[-1]
    sp = strokes[k].spine
    return sp[-1] if entry.get(k, True) else sp[0]


def test_the_walk_ends_nearest_end_near():
    strokes = _h_strokes()
    nodes, edges, adj = s6._build_travel_graph(strokes)
    start = (-1.0, 0.0)                      # the needle is by the left stem's foot
    for target in ((11.0, 10.0), (11.0, 0.0), (-1.0, 10.0)):
        order, entry = s6._euler_stroke_order(nodes, edges, adj, len(strokes), start,
                                              end_near=target)
        assert sorted(order) == [0, 1, 2]
        end = _walk_end(strokes, order, entry)
        far = max(math.dist(target, p) for st in strokes for p in (st.spine[0], st.spine[-1]))
        assert math.dist(end, target) < 2.0, (target, end, order, entry)
        assert math.dist(end, target) < far


def test_without_end_near_the_walk_is_the_shipped_one():
    strokes = _h_strokes()
    nodes, edges, adj = s6._build_travel_graph(strokes)
    start = (-1.0, 0.0)
    plain = s6._euler_stroke_order(nodes, edges, adj, len(strokes), start)
    explicit = s6._euler_stroke_order(nodes, edges, adj, len(strokes), start, end_near=None)
    assert explicit == plain


def test_the_exit_lever_takes_the_letter_hops_down_to_the_typed_words(exit_on):
    """13 -> 9 trims, letter-to-letter 6 -> 3 measured when the lever went
    ON (the OFF arm is gone from the config); the typed word's 3. On the
    folded engine, with rail comp, tip caps and the crown cover riding along,
    it reads 5 (re-measured 2026-11-19): still under the 6 the lever started
    from."""
    r_on, p_on = exit_on
    hops_on = _trims_by_cause(r_on, p_on).get("letter-to-shape", 0)
    assert hops_on <= 5, hops_on


# --- the underlay lever: the underlay ends where the column enters ---------------

def _first_stroke_runs(runs):
    """The first stroke's runs: from the first underlay to the first column."""
    out = []
    for r in runs:
        out.append(r)
        if r.kind == stitches.SATIN:
            break
    return out


@pytest.mark.parametrize("flag", [False, True])
def test_on_a_bar_the_underlay_reaches_the_columns_first_cross(flag):
    """A 3 x 20 mm bar: its skeleton stops half a width short of each cap and
    the column is extended to the cap. Off, the underlay ends short and the
    hop to the column is over the tiny-stitch floor; on, the underlay's last
    point IS the column's first."""
    bar = Polygon([(0, 0), (20, 0), (20, 3), (0, 3)])
    runs, report = s6.satin_shape(bar, "bar", underlay_style="center", trim_at_mm=3.0,
                                  underlay_on_column=flag)
    assert not report["empty"]
    first = _first_stroke_runs(runs)
    assert first[0].kind == stitches.UNDERLAY and first[-1].kind == stitches.SATIN
    gap = math.dist(first[-2].points[-1], first[-1].points[0])
    if flag:
        assert gap < machine.TINY_STITCH_MM, gap
    else:
        assert gap >= machine.TINY_STITCH_MM, gap


def test_the_underlay_lever_removes_the_underlay_to_column_trims(exit_on, both_on):
    """Four on the fixture without the lever (3.3-4.2 mm hops on its split
    columns); none with it."""
    r_off, p_off = exit_on
    r_on, p_on = both_on
    assert _trims_by_cause(r_off, p_off).get("underlay->satin", 0) >= 3
    assert _trims_by_cause(r_on, p_on).get("underlay->satin", 0) == 0
    assert p_on.stats.trims < p_off.stats.trims


def test_the_underlay_lever_costs_stitches_and_says_so(exit_on, both_on):
    """+9% on the fixture (1,969 -> 2,146): the underlay covers the cap
    extensions and the zigzag appears on strokes whose raw spine ran into a
    junction blob. Pinned as a ceiling so a cheaper build can lower it."""
    _r1, p_off = exit_on
    _r2, p_on = both_on
    assert p_on.stats.stitch_count <= 1.15 * p_off.stats.stitch_count


# --- both ----------------------------------------------------------------------

def test_both_levers_together_take_the_fixture_under_eighteen_trims(both_on):
    """13 -> 8 measured; every trim left is the first needle-down, the cap,
    a letter-to-letter hop (four here: the underlay lever moves where a
    column starts, and one hop the exit lever alone kept under `trim_at`
    reads over it with both), or a refused walk. On the folded engine (rail
    comp, tip caps and the crown cover ride along, re-measured 2026-11-19)
    both levers read 17 trims against the exit lever's 20, with 5
    letter-to-letter hops."""
    r_on, p_on = both_on
    assert p_on.stats.trims <= 17
    by = _trims_by_cause(r_on, p_on)
    assert by.get("underlay->satin", 0) == 0
    assert by.get("letter-to-shape", 0) <= 5


# 2026-11-20 (bundle roll-forward): the numbers here were read without the photo lane's
# phantom-blend dissolve (item 46, folded into the code 2026-11-20; `legacy_engine` patched
# its False path back). They are read on today's engine now.
