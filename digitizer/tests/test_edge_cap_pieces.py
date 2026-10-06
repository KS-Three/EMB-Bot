"""The cap sews each stretch of the edge in the thread beside it, and each
stretch is addressable (`cap:<x>:<y>`), so the Studio can select, recolour or
delete one the way it does a shape.

Kent, 2026-10-06, on the Instagram icon: the bean outline did not follow the
colour it was next to, and he wanted to click it like a recognised shape.
"""
from __future__ import annotations

from types import SimpleNamespace

from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric
from digitizer_core.regions import Region, apply_shape_edits
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence
from digitizer_core.stitches import CAP_PIECE_PREFIX
from digitizer_core.threads import CHART
from digitizer_core.warnings_codes import SHAPE_EDIT_UNKNOWN_ID

FAB = get_fabric("pique_knit")


def bar(w, h, cx=0.0, cy=0.0):
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly, sid, thread, layer):
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer})


# Two abutting bars in different threads: the silhouette passes both colours.
BOTH = [region(bar(15, 30, cx=-7.5), "L", 3, 0),
        region(bar(15, 30, cx=7.5), "R", 5, 1)]
ONE = [region(bar(30, 30), "A", 3, 0)]


def plan_for(regions, **cfg_kw):
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)
    return SimpleNamespace(blocks=blocks, warnings=warnings)


def cap_runs(plan):
    return [(b.thread_index, r) for b in plan.blocks for r in b.runs
            if r.shape_id == "__edge_cap__"]


def test_each_stretch_sews_in_the_thread_beside_it():
    plan = plan_for(BOTH)
    assert {t for t, _ in cap_runs(plan)} == {3, 5}
    for t, run in cap_runs(plan):
        xs = [p[0] for p in run.points]
        # Left bar is thread 3, right is thread 5: a stretch in thread 3 must
        # sit on the left half, and vice versa (the seam is at x = 0).
        mean = sum(xs) / len(xs)
        assert (mean < 0) == (t == 3)


def test_off_restores_the_single_block():
    plan = plan_for(BOTH, edge_cap_follow_adjacent=False)
    assert len({t for t, _ in cap_runs(plan)}) == 1
    assert all(r.piece == "" for _, r in cap_runs(plan))


def test_every_stretch_has_a_unique_cap_id():
    ids = [r.piece for _, r in cap_runs(plan_for(BOTH))]
    assert ids and all(i.startswith(CAP_PIECE_PREFIX) for i in ids)
    assert len(ids) == len(set(ids))


def test_a_one_colour_edge_is_one_block_of_the_emitters_own_runs():
    on = plan_for(ONE)
    off = plan_for(ONE, edge_cap_follow_adjacent=False)
    a = [(t, r.points, r.jump, r.trim) for t, r in cap_runs(on)]
    b = [(t, r.points, r.jump, r.trim) for t, r in cap_runs(off)]
    assert a == b
    assert all(r.piece.startswith(CAP_PIECE_PREFIX) for _, r in cap_runs(on))


def test_ids_do_not_depend_on_the_thread():
    ids = {r.piece for _, r in cap_runs(plan_for(BOTH))}
    victim = sorted(ids)[0]
    recoloured = plan_for(BOTH, shape_overrides={victim: {"thread_index": 7}})
    assert {r.piece for _, r in cap_runs(recoloured)} == ids


def test_a_deleted_stretch_is_not_sewn():
    base = cap_runs(plan_for(BOTH))
    victim = base[0][1].piece
    after = cap_runs(plan_for(BOTH, deleted_shape_ids=[victim]))
    assert victim not in {r.piece for _, r in after}
    assert len(after) == len(base) - 1


def test_deleting_every_stretch_leaves_no_cap_and_no_crash():
    base = cap_runs(plan_for(BOTH))
    plan = plan_for(BOTH, deleted_shape_ids=[r.piece for _, r in base])
    assert cap_runs(plan) == []


def test_a_recoloured_stretch_sews_in_the_chosen_thread():
    base = cap_runs(plan_for(BOTH))
    victim_thread, victim = base[0]
    other = 7 if victim_thread != 7 else 8
    after = {r.piece: t for t, r in cap_runs(
        plan_for(BOTH, shape_overrides={victim.piece: {"thread_index": other}}))}
    assert after[victim.piece] == other


def test_a_cap_id_is_not_an_unknown_shape():
    regions = [region(bar(10, 10), "A", 3, 0)]
    _, _, warnings = apply_shape_edits(
        regions, [3], ["cap:4:5"], {"cap:6:7": {"thread_index": 2}}, CHART)
    assert not [w for w in warnings if w["code"] == SHAPE_EDIT_UNKNOWN_ID]
    _, _, warnings = apply_shape_edits(regions, [3], ["nope"], {}, CHART)
    assert [w for w in warnings if w["code"] == SHAPE_EDIT_UNKNOWN_ID]
