"""`cfg.edge_cap_fold_into_colour` -- the cap's stretches sew inside their
own cone's last artwork block when nothing later touches them.

DEFAULT OFF. Photo/tonal v1 spec, engineering item "sequencing trim thrash":
the follow-adjacent cap adds one machine stop per cone its stretches touch,
every one a cone the artwork already sewed. Measured with
`tools/cap_fold_ab.py` (owl through the photo route: 32 -> 28 stops, stitches
and trims unchanged). What these pin: the flag reorders and never adds or
removes a stitch, it never folds a stretch something later sews near, and
off is the shipped plan exactly.
"""
from __future__ import annotations

from collections import Counter
from types import SimpleNamespace

from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric, machine
from digitizer_core.regions import Region
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import _cap_fold_host, sequence
from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
from digitizer_core.threads import CHART

FAB = get_fabric("pique_knit")


def bar(w: float, h: float, cx: float = 0.0, cy: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, cy - h / 2)


def region(poly: Polygon, sid: str, thread: int, layer: int) -> Region:
    return Region(shape_id=sid, polygon=poly, thread_index=thread,
                  thread_number=CHART[thread].number, area_mm2=poly.area,
                  meta={"layer": layer})


def plan_for(regions, **cfg_kw):
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)
    return SimpleNamespace(blocks=blocks, warnings=warnings)


def is_cap(r) -> bool:
    return r.shape_id == "__edge_cap__"


def stats(plan):
    return StitchPlan(blocks=plan.blocks, palette=[]).stats


def points(blocks) -> Counter:
    return Counter(p for b in blocks for r in b.runs for p in r.points)


# Two abutting fields: the left one's cap stretches meet the right one's rows
# at the seam ends, so only the LAST artwork cone may fold.
ABUT = [region(bar(15, 30, cx=-7.5), "L", 3, 0),
        region(bar(15, 30, cx=7.5), "R", 5, 1)]
# Two fields 20 mm apart: nothing sewn later comes near either cap.
APART = [region(bar(15, 30, cx=-17.5), "L", 3, 0),
         region(bar(15, 30, cx=17.5), "R", 5, 1)]


def test_the_default_is_off():
    assert PipelineConfig().edge_cap_fold_into_colour is False


def test_off_every_cap_run_sits_in_a_cap_only_block_after_the_artwork():
    """The shipped structure the flag departs from, pinned on both fixtures."""
    for regions in (APART, ABUT):
        blocks = plan_for(regions).blocks
        kinds = [all(is_cap(r) for r in b.runs if r.points) for b in blocks]
        first = kinds.index(True)
        assert all(kinds[first:]) and not any(kinds[:first])
        assert not any(is_cap(r) for b in blocks[:first] for r in b.runs)


def test_untouched_stretches_fold_and_save_every_cap_stop():
    off = plan_for(APART)
    on = plan_for(APART, edge_cap_fold_into_colour=True)
    assert len(off.blocks) == 4          # two artwork blocks + two cap blocks
    assert len(on.blocks) == 2
    assert [b.thread_index for b in on.blocks] == [3, 5]
    for b in on.blocks:
        assert any(is_cap(r) for r in b.runs)
        # The cap still sews AFTER its own colour's rows.
        first_cap = next(i for i, r in enumerate(b.runs) if is_cap(r))
        assert all(is_cap(r) for r in b.runs[first_cap:])


def test_it_reorders_and_never_adds_or_removes_a_stitch_or_a_cut():
    """Counted off the emitted machine stream (`StitchPlan.stats`), the one
    the file is encoded from: the same stitches, the same trims, and exactly
    one colour change fewer per folded cone."""
    for regions, folded in ((APART, 2), (ABUT, 1)):
        off = plan_for(regions)
        on = plan_for(regions, edge_cap_fold_into_colour=True)
        assert points(on.blocks) == points(off.blocks)
        s_off, s_on = stats(off), stats(on)
        assert s_on.stitch_count == s_off.stitch_count
        assert s_on.trims == s_off.trims
        assert s_on.color_changes == s_off.color_changes - folded


def test_the_service_does_not_call_a_host_block_the_design_edge():
    """`design_edge` means "no review shape behind this block"; a host block
    sews its own shapes and the cap, so it is not that row."""
    from digitizer_service.app import _block_shape_ids, _is_edge_cap
    on = plan_for(APART, edge_cap_fold_into_colour=True)
    for b in on.blocks:
        assert not _is_edge_cap(b)
        assert _block_shape_ids(b)
    off = plan_for(APART)
    assert [_is_edge_cap(b) for b in off.blocks] == [False, False, True, True]


def test_a_stretch_something_later_sews_near_keeps_its_own_block():
    """L's stretches end where R's rows begin, and R sews after L, so L's cap
    must stay on top -- in its own block after R. R is the last artwork cone,
    so its stretches fold."""
    off = plan_for(ABUT)
    on = plan_for(ABUT, edge_cap_fold_into_colour=True)
    assert len(off.blocks) == 4
    assert len(on.blocks) == 3
    assert [b.thread_index for b in on.blocks] == [3, 5, 3]
    assert all(is_cap(r) for r in on.blocks[2].runs)


def _block(thread, *runs, step=None):
    return StitchBlock(thread_index=thread, thread_number=CHART[thread].number,
                       rgb=tuple(CHART[thread].rgb),
                       runs=[StitchRun(points=list(p), shape_id="s") for p in runs],
                       step=step)


CLEAR = machine.BORDER_WIDTH_MM / 2.0
CAP = [StitchRun(points=[(0.0, 0.0), (10.0, 0.0)], shape_id="__edge_cap__")]


def test_the_host_is_the_cones_last_artwork_block():
    blocks = [_block(1, [(0, 5), (10, 5)]), _block(2, [(0, 20), (10, 20)]),
              _block(1, [(0, 30), (10, 30)])]
    assert _cap_fold_host(blocks, 3, 1, CAP, CLEAR) is blocks[2]


def test_no_host_when_the_cone_sewed_no_artwork():
    blocks = [_block(1, [(0, 5), (10, 5)])]
    assert _cap_fold_host(blocks, 1, 7, CAP, CLEAR) is None


def test_a_later_stitch_inside_the_clearance_refuses_the_fold():
    near = CLEAR * 0.9
    blocks = [_block(1, [(0, 5), (10, 5)]), _block(2, [(5, near), (5, 9)])]
    assert _cap_fold_host(blocks, 2, 1, CAP, CLEAR) is None
    far = CLEAR * 1.1
    blocks = [_block(1, [(0, 5), (10, 5)]), _block(2, [(5, far), (5, 9)])]
    assert _cap_fold_host(blocks, 2, 1, CAP, CLEAR) is blocks[0]


def test_an_operator_step_block_is_never_a_host():
    """Appliqué and puff blocks end in a stop the operator acts on; a cap
    appended to one would sew before that action, not after the artwork."""
    blocks = [_block(1, [(0, 5), (10, 5)], step={"action": "place fabric"})]
    assert _cap_fold_host(blocks, 1, 1, CAP, CLEAR) is None


def test_blocks_past_the_artwork_are_not_read_as_later_artwork():
    """Other cones' cap blocks are appended after `n_art`; they meet this
    cone's stretches end to end and do not refuse the fold."""
    blocks = [_block(1, [(0, 5), (10, 5)]), _block(2, [(0, 0), (10, 0)])]
    assert _cap_fold_host(blocks, 1, 1, CAP, CLEAR) is blocks[0]
