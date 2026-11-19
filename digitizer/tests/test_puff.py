"""3D puff (docs/superpowers/specs/2026-11-19-3d-puff-design.md): config switch,
constants, the per-shape eligibility test, and one shape's construction
(end-capped puff satin, ties, tack-down)."""
from __future__ import annotations

import math
import statistics
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from digitizer_core import PipelineConfig, machine, stitches
from digitizer_core.stage6_puff import puff_eligible, wants_puff


def _region(w_mm: float, h_mm: float = 30.0, **meta):
    return SimpleNamespace(polygon=box(0, 0, h_mm, w_mm), meta=dict(meta))


def test_puff_off_by_default():
    cfg = PipelineConfig()
    assert cfg.puff is False
    assert cfg.puff_mode == "all"


def test_wants_puff_modes():
    off = PipelineConfig(puff=False)
    assert wants_puff(_region(4, puff=True), off) is False
    assert wants_puff(_region(4), off) is False

    allm = PipelineConfig(puff=True, puff_mode="all")
    assert wants_puff(_region(4), allm) is True
    assert wants_puff(_region(4, puff=False), allm) is False
    assert wants_puff(_region(4, puff=True), allm) is True

    sel = PipelineConfig(puff=True, puff_mode="select")
    assert wants_puff(_region(4), sel) is False
    assert wants_puff(_region(4, puff=False), sel) is False
    assert wants_puff(_region(4, puff=True), sel) is True


def test_puff_eligible_width():
    cfg = PipelineConfig(puff=True)
    assert puff_eligible(_region(4), cfg) == (True, "")
    # Thin uses the skeleton mean (reads 1.8 as 1.9); wide uses the widest
    # inscribed circle, which is exact on a bar (the mean read 14 as 9.8).
    assert puff_eligible(_region(1.8), cfg) == (False, "too thin for foam (1.9 mm)")
    assert puff_eligible(_region(14), cfg) == (False, "too wide to puff (14.0 mm)")


def test_puff_eligible_ignores_flat_satin_ceiling():
    # 8 mm is past the flat satin ceiling (5.0) but inside the puff band.
    assert puff_eligible(_region(8), PipelineConfig(puff=True)) == (True, "")


def test_puff_eligible_ring_uses_ring_width_not_hole_blind_circle():
    from shapely.geometry import Point
    ring = Point(0, 0).buffer(10, 64).difference(Point(0, 0).buffer(6, 64))
    reg = SimpleNamespace(polygon=ring, meta={})
    assert puff_eligible(reg, PipelineConfig(puff=True)) == (True, "")


def test_puff_eligible_multipolygon_does_not_raise():
    from shapely.geometry import MultiPolygon
    mp = MultiPolygon([box(0, 0, 30, 4), box(0, 20, 30, 24)])
    reg = SimpleNamespace(polygon=mp, meta={})
    assert puff_eligible(reg, PipelineConfig(puff=True)) == (True, "")


# --- Task 3: construction for one shape ------------------------------------

BAR = box(0, 0, 30, 4)  # 4 x 30 mm bar, short ends at x=0 and x=30
RING = Point(0, 0).buffer(10, 64).difference(Point(0, 0).buffer(6, 64))
TEE = unary_union([box(0, 0, 30, 4), box(13, 4, 17, 24)])


def _puff(poly):
    from digitizer_core.stage6_puff import puff_shape
    return puff_shape(poly, "p", PipelineConfig(puff=True))


def _all_points(runs):
    return [p for r in runs for p in r.points]


def _covered(segment: LineString, pts, reach=0.3, step=0.05) -> float:
    """Fraction of `segment` within `reach` of some needle point."""
    n = max(1, int(segment.length / step))
    hit = 0
    for k in range(n + 1):
        q = segment.interpolate(k / n, normalized=True)
        if any(math.hypot(q.x - x, q.y - y) <= reach for x, y in pts):
            hit += 1
    return hit / (n + 1)


def test_puff_no_underlay():
    runs = _puff(BAR)
    assert runs
    assert all(r.kind != stitches.UNDERLAY for r in runs)


def test_puff_density():
    runs = [max(_puff(BAR), key=lambda r: len(r.points))]  # the top satin
    gaps = []
    for r in runs:
        pts = r.points[r.tie_in_pts:]
        mids = [((pts[i][0] + pts[i + 1][0]) / 2) for i in range(0, len(pts) - 1, 2)]
        gaps += [abs(b - a) for a, b in zip(mids, mids[1:])]
    assert abs(statistics.median(gaps) - machine.PUFF_SATIN_SPACING_MM) <= 0.02


@pytest.mark.parametrize("x", [0.0, 30.0])
def test_puff_ends_closed(x):
    pts = _all_points(_puff(BAR))
    assert _covered(LineString([(x, 0), (x, 4)]), pts) >= 0.8


def test_puff_end_caps_sew_before_top_satin():
    runs = _puff(BAR)
    top = max(range(len(runs)), key=lambda i: len(runs[i].points))
    reach = machine.PUFF_CAP_DEPTH_MM + 0.01
    caps = [i for i, r in enumerate(runs)
            if r.kind != stitches.TRAVEL and all(min(x, 30 - x) <= reach for x, _ in r.points[r.tie_in_pts:])]
    assert len(caps) == 2  # one per short end
    assert all(i < top for i in caps)


def test_puff_counter_closed():
    from digitizer_core.stage6_puff import puff_tackdown
    pts = _all_points(_puff(RING))
    inner = LineString(RING.interiors[0].coords)
    assert _covered(inner, pts) >= 0.8

    tack = puff_tackdown([RING], ["p"], PipelineConfig(puff=True))
    for ring in (RING.exterior, RING.interiors[0]):
        line = LineString(ring.coords)
        assert any(
            len(r.points) > 3
            and max(line.distance(Point(p)) for p in r.points) <= 0.3
            for r in tack
        ), "no tack-down run round this ring"


def test_puff_no_short_stitches():
    # §3.6: short stitches dig into the foam. Every top-satin penetration
    # stays on the shape's edge (ties and cap rows excluded).
    runs = _puff(BAR)
    top_i = max(range(len(runs)), key=lambda i: len(runs[i].points))
    top = runs[top_i]
    pts = top.points[top.tie_in_pts:]
    if top_i == len(runs) - 1:
        pts = pts[:-machine.PUFF_TIE_STITCHES]
    # 0.2, not 0.15: satin_shape's own rail sits 0.17 mm in on one side of
    # this bar (y=0.167). A short stitch is retracted 0.77 mm.
    worst = max(BAR.boundary.distance(Point(p)) for p in pts)
    assert worst <= 0.2, f"a penetration {worst:.2f} mm inside the edge"


def test_puff_tackdown_is_inset():
    from digitizer_core.stage6_puff import puff_tackdown
    tack = puff_tackdown([BAR], ["p"], PipelineConfig(puff=True))
    assert len(tack) == 1
    inset = BAR.buffer(-machine.PUFF_INSET_MM, join_style=2)
    pts = tack[0].points
    for p in pts:
        assert abs(inset.exterior.distance(Point(p))) < 1e-6
    # §3.7: two passes -- round the ring and back over the same path.
    n = len(pts) // 2
    assert len(pts) == 2 * n + 1
    assert pts[0] == pts[n] == pts[-1]
    assert pts[n:] == pts[:n + 1][::-1]


def _bounce(seq) -> bool:
    return all(seq[i] == seq[i + 2] for i in range(len(seq) - 2)) and \
        all(0 < math.dist(a, b) <= machine.TIE_STITCH_MM + 1e-9
            for a, b in zip(seq, seq[1:]))


def test_puff_ties():
    n = machine.PUFF_TIE_STITCHES
    for poly in (BAR, RING):
        runs = _puff(poly)
        first, last = runs[0], runs[-1]
        assert first.tie_in_pts == n
        assert _bounce(first.points[:n + 1])
        assert _bounce(last.points[-(n + 1):])
    # tie_run's own default is untouched.
    assert len(stitches.tie_run((0, 0), (5, 0)).points) == machine.TIE_STITCHES + 2


def test_puff_junction_overlap():
    # The stem must run into the bar by at least the overlap, not butt it.
    runs = [r for r in _puff(TEE) if r.kind == stitches.SATIN]
    stem_low = min(
        min(p[1] for p in r.points)
        for r in runs if min(p[0] for p in r.points) > 10
    )
    assert stem_low <= 4.0 - machine.PUFF_JUNCTION_OVERLAP_MM


def test_puff_tee_caps_only_free_ends():
    pts = _all_points(_puff(TEE))
    # bar ends and the stem's top are free; all three close.
    assert _covered(LineString([(0, 0), (0, 4)]), pts) >= 0.8
    assert _covered(LineString([(30, 0), (30, 4)]), pts) >= 0.8
    assert _covered(LineString([(13, 24), (17, 24)]), pts) >= 0.8


# --- The puff pass and sequencing (Task 4) ------------------------------------

from digitizer_core import digitize, export  # noqa: E402
from digitizer_core.stage6_applique import COLOR_CHANGE, Step, assert_steps_valid  # noqa: E402
from digitizer_core.warnings_codes import PUFF_NONE_ELIGIBLE, PUFF_SHAPE_INELIGIBLE  # noqa: E402
from tests.conftest import TESTDATA, cfg  # noqa: E402


def _is_puff(block) -> bool:
    return block.step is not None and block.step["code"].startswith("PUFF")


@pytest.fixture(scope="module")
def logo_puff():
    return digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front", puff=True))


@pytest.fixture(scope="module")
def tires_puff():
    """The puff-on end-to-end fixture. logo_whitebg.png has no shape stage 7
    sews as a satin column in the puff band (its one in-band candidate is
    pinned `tier: "fill"` by `columns.py`), so it puffs nothing;
    logo_script_tires.png puffs one thread and sews a flat block of that
    same thread straight before the puff blocks."""
    return digitize(TESTDATA / "logo_script_tires.png", cfg(garment_id="hat_front", puff=True))


class _PRegion:
    def __init__(self, poly, thread_index, meta):
        self.polygon = poly
        self.thread_index = thread_index
        self.meta = meta


class _PPlanned:
    """The minimal `PlannedRegion` surface `puff_pass` reads."""

    def __init__(self, poly, thread_index, sew_index, shape_id, layer=0, **meta):
        self.region = _PRegion(poly, thread_index, {"layer": layer, **meta})
        self.polygon = poly
        self.layer = layer
        self.sew_index = sew_index
        self.shape_id = shape_id


def _run_puff_pass(planned, **cfg_kw):
    from digitizer_core.stage6_puff import puff_pass
    from digitizer_core.threads import chart_for
    c = cfg(puff=True, **cfg_kw)
    return puff_pass(planned, c, chart_for(c))


BAR_A = box(0, 0, 30, 5)          # 5 mm wide: inside the puff band
BAR_B = box(0, 20, 30, 25)
THIN_A = box(0, 40, 30, 41)       # 1 mm: too thin for foam
THIN_B = box(0, 50, 30, 51)


def test_puff_off_is_byte_identical():
    a = digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front"))[1]
    b = digitize(TESTDATA / "logo_whitebg.png", cfg(garment_id="hat_front", puff=False))[1]
    assert export.export_dst(a) == export.export_dst(b)
    assert all(blk.step is None for blk in a.blocks)


def test_puff_pass_off_returns_planned_untouched():
    from digitizer_core.stage6_puff import puff_pass
    from digitizer_core.threads import chart_for
    planned = [_PPlanned(BAR_A, 20, 0, "A", puff=True)]
    c = cfg()
    assert puff_pass(planned, c, chart_for(c)) == ([], [], planned)


def test_puff_blocks_last(tires_puff):
    _result, plan = tires_puff
    flags = [_is_puff(b) for b in plan.blocks]
    assert any(flags), "logo_script_tires has a puffable column; puff on must puff it"
    first = flags.index(True)
    assert all(flags[first:]), "every puff block comes after every flat block"
    puff = plan.blocks[first:]
    assert len(puff) % 2 == 0
    codes = [b.step["code"] for b in puff]
    assert codes == ["PUFF_TACKDOWN", "PUFF"] * (len(puff) // 2)
    threads = [b.thread_index for b in puff]
    assert all(threads[i] == threads[i + 1] for i in range(0, len(threads), 2))
    assert len(set(threads[::2])) == len(threads) // 2, "one tack-down per puff thread"
    # Index is the block's 1-based position in the plan.
    assert [b.step["index"] for b in puff] == list(range(first + 1, len(plan.blocks) + 1))
    # Puffed shapes sew only in puff blocks, and never as tatami.
    puff_ids = {r.shape_id for b in puff for r in b.runs}
    flat_ids = {r.shape_id for b in plan.blocks[:first] for r in b.runs}
    assert not puff_ids & flat_ids
    assert not any(r.kind == stitches.FILL for b in puff for r in b.runs)


def test_puff_steps_valid(tires_puff):
    _result, plan = tires_puff
    puff = [b for b in plan.blocks if _is_puff(b)]
    steps = [Step(code=b.step["code"], label=b.step["label"], runs=b.runs,
                  action=b.step["action"], function=b.step["function"]) for b in puff]
    assert_steps_valid(steps)
    td = [b.step for b in puff if b.step["code"] == "PUFF_TACKDOWN"]
    ps = [b.step for b in puff if b.step["code"] == "PUFF"]
    assert td and ps
    assert {(s["label"], s["action"], s["function"]) for s in td} == {
        ("Puff outline", "Stop: lay 3 mm puff foam over the outline, then continue",
         COLOR_CHANGE)}
    assert {(s["label"], s["action"], s["function"]) for s in ps} == {
        ("3D puff", "Tear away the excess foam, then continue", COLOR_CHANGE)}


def test_puff_on_nothing_eligible_is_off():
    planned = [_PPlanned(THIN_A, 20, 0, "T1"), _PPlanned(THIN_B, 21, 1, "T2")]
    blocks, warnings, remaining = _run_puff_pass(planned)
    assert blocks == []
    assert remaining == planned
    assert [w["code"] for w in warnings].count(PUFF_NONE_ELIGIBLE) == 1


def test_puff_on_nothing_eligible_is_off_end_to_end(tmp_path):
    """A design of only thin strokes sews exactly what it sews with puff off."""
    import cv2
    import numpy as np
    # Transparent ground: a white one is itself a sewn (and puffable) shape.
    img = np.zeros((400, 800, 4), np.uint8)
    for y in (100, 200, 300):
        cv2.line(img, (60, y), (740, y), (0, 0, 0, 255), 8)  # ~1.1 mm strokes
    path = tmp_path / "thin.png"
    cv2.imwrite(str(path), img)
    a = digitize(path, cfg(garment_id="hat_front"))[1]
    b = digitize(path, cfg(garment_id="hat_front", puff=True))[1]
    assert export.export_dst(a) == export.export_dst(b)
    assert [w["code"] for w in b.warnings].count(PUFF_NONE_ELIGIBLE) == 1
    assert PUFF_NONE_ELIGIBLE not in [w["code"] for w in a.warnings]


def test_puff_none_wanted_is_silent():
    # Select mode with nothing ticked: nothing was wanted, so nothing to say.
    planned = [_PPlanned(THIN_A, 20, 0, "T1")]
    blocks, warnings, remaining = _run_puff_pass(planned, puff_mode="select")
    assert (blocks, warnings, remaining) == ([], [], planned)


def test_puff_two_threads_two_stops():
    planned = [_PPlanned(BAR_A, 20, 0, "A"), _PPlanned(BAR_B, 21, 1, "B")]
    blocks, warnings, remaining = _run_puff_pass(planned)
    assert remaining == []
    assert warnings == []
    assert [b.step["code"] for b in blocks] == ["PUFF_TACKDOWN", "PUFF"] * 2
    assert [b.thread_index for b in blocks] == [20, 20, 21, 21]
    assert [b.step["index"] for b in blocks] == [1, 2, 3, 4]
    for b in blocks:
        assert b.runs[0].jump and b.runs[0].trim
        assert b.step["thread"] == b.thread_number


def test_puff_same_thread_shapes_share_one_stop():
    planned = [_PPlanned(BAR_A, 20, 0, "A"), _PPlanned(BAR_B, 20, 1, "B")]
    blocks, _w, _rem = _run_puff_pass(planned)
    assert [b.step["code"] for b in blocks] == ["PUFF_TACKDOWN", "PUFF"]
    assert {r.shape_id for r in blocks[0].runs} == {"A", "B"}
    assert {r.shape_id for r in blocks[1].runs} == {"A", "B"}
    # A -> B is a lift (cut at this gap), never a needle-down drag over foam.
    top = blocks[1].runs
    k = next(i for i, r in enumerate(top) if r.shape_id == "B")
    gap = math.dist(top[k - 1].points[-1], top[k].points[0])
    assert top[k].jump is True
    assert top[k].trim is (gap >= machine.TRIM_AT_MM)
    assert gap >= machine.TRIM_AT_MM  # the stubs sit 15+ mm apart: a cut


def _bar_and_line(path):
    """Transparent ground, one colour: a ~5 mm bar (puffable column) and a
    ~1.4 mm line (too thin for foam), so the flat line and the puffed bar
    share one thread and sew as ADJACENT blocks."""
    import cv2
    import numpy as np
    img = np.zeros((400, 800, 4), np.uint8)
    cv2.rectangle(img, (100, 100), (700, 137), (0, 0, 0, 255), -1)
    cv2.line(img, (100, 250), (700, 250), (0, 0, 0, 255), 8)
    cv2.imwrite(str(path), img)
    return path


def test_puff_not_merged_with_flat(tmp_path):
    """A flat shape on the puff thread, sewn straight before its puff
    blocks: with `merge_adjacent_same_thread` (default True) the puff blocks
    stay blocks of their own, holding only puffed shapes."""
    path = _bar_and_line(tmp_path / "bar_line.png")
    c = cfg(garment_id="hat_front", puff=True)
    assert c.merge_adjacent_same_thread is True
    plan = digitize(path, c)[1]
    puff = [b for b in plan.blocks if _is_puff(b)]
    assert [b.step["code"] for b in puff] == ["PUFF_TACKDOWN", "PUFF"]
    puff_ids = {r.shape_id for b in puff for r in b.runs}
    for b in plan.blocks:
        ids = {r.shape_id for r in b.runs}
        if _is_puff(b):
            assert ids <= puff_ids
        else:
            assert not ids & puff_ids
    k = plan.blocks.index(puff[0])
    assert k > 0 and not _is_puff(plan.blocks[k - 1])
    assert plan.blocks[k - 1].thread_index == puff[0].thread_index,         "the fixture must sew a flat block on the puff thread right before it"


def test_puff_not_merged_with_flat_tires(tires_puff):
    _result, plan = tires_puff
    puff = [b for b in plan.blocks if _is_puff(b)]
    k = plan.blocks.index(puff[0])
    assert plan.blocks[k - 1].step is None
    assert plan.blocks[k - 1].thread_index == puff[0].thread_index
    puff_ids = {r.shape_id for b in puff for r in b.runs}
    assert not puff_ids & {r.shape_id for r in plan.blocks[k - 1].runs}


def test_puff_not_merged_stub():
    """Unit level: the flat shape on the puff thread goes back to the loop."""
    planned = [_PPlanned(BAR_A, 20, 0, "A"), _PPlanned(THIN_A, 20, 1, "F", puff=False)]
    blocks, _w, remaining = _run_puff_pass(planned)
    assert [p.shape_id for p in remaining] == ["F"]
    assert all({r.shape_id for r in b.runs} == {"A"} for b in blocks)


def test_puff_ineligible_warned():
    planned = [_PPlanned(BAR_A, 20, 0, "A"), _PPlanned(THIN_A, 21, 1, "T1")]
    blocks, warnings, remaining = _run_puff_pass(planned, puff_mode="all")
    assert [p.shape_id for p in remaining] == ["T1"]
    hits = [w for w in warnings if w["code"] == PUFF_SHAPE_INELIGIBLE]
    assert len(hits) == 1
    assert hits[0]["shape_id"] == "T1"
    assert hits[0]["reason"].startswith("too thin for foam")
    assert PUFF_NONE_ELIGIBLE not in [w["code"] for w in warnings]
    assert {r.shape_id for b in blocks for r in b.runs} == {"A"}


def test_puff_ineligible_warned_end_to_end(logo_puff):
    _result, plan = logo_puff
    hits = {w["shape_id"] for w in plan.warnings if w["code"] == PUFF_SHAPE_INELIGIBLE}
    # Sdf9f8b3c is logo_whitebg's 0.7 mm sliver on thread 119.
    assert "Sdf9f8b3c" in hits
    puff_ids = {r.shape_id for b in plan.blocks if _is_puff(b) for r in b.runs}
    assert not hits & puff_ids


def test_puff_never_puffs_the_ground(logo_puff):
    """Mode "all" on logo_whitebg.png: the ground (stage 4's
    `enclosed_background` tag) sews flat with a "not a column shape"
    warning. Before the column gate it was the 14.1 mm ground that was
    refused only for width; on a narrower ground it puffed."""
    from digitizer_core.stage6_puff import NOT_A_COLUMN
    result, plan = logo_puff
    ground = {r.shape_id for r in result.regions if r.meta.get("enclosed_background")}
    assert ground, "logo_whitebg's white ground carries the tag"
    puff_ids = {r.shape_id for b in plan.blocks if _is_puff(b) for r in b.runs}
    assert not ground & puff_ids
    not_col = {w["shape_id"] for w in plan.warnings
               if w["code"] == PUFF_SHAPE_INELIGIBLE and w["reason"] == NOT_A_COLUMN}
    assert ground <= not_col
    # No shape here is a satin column in the puff band, so nothing puffs.
    assert puff_ids == set()
    assert [w["code"] for w in plan.warnings].count(PUFF_NONE_ELIGIBLE) == 1


def test_puff_puffs_only_columns(tires_puff):
    from digitizer_core.stage6_puff import NOT_A_COLUMN
    result, plan = tires_puff
    puff_ids = {r.shape_id for b in plan.blocks if _is_puff(b) for r in b.runs}
    assert puff_ids
    not_col = {w["shape_id"] for w in plan.warnings
               if w["code"] == PUFF_SHAPE_INELIGIBLE and w["reason"] == NOT_A_COLUMN}
    ground = {r.shape_id for r in result.regions if r.meta.get("enclosed_background")}
    assert not (not_col | ground) & puff_ids


def test_puff_white_ground_not_puffed(tmp_path):
    """A white ground stage 1 could not find (BACKGROUND_ABSENT, no tag) is
    no column either: thin strokes on white sew exactly as with puff off."""
    import cv2
    import numpy as np
    img = np.full((400, 800, 3), 255, np.uint8)
    for y in (100, 200, 300):
        cv2.line(img, (60, y), (740, y), (0, 0, 0), 8)
    path = tmp_path / "thin_white.png"
    cv2.imwrite(str(path), img)
    a = digitize(path, cfg(garment_id="hat_front"))[1]
    b = digitize(path, cfg(garment_id="hat_front", puff=True))[1]
    assert not any(_is_puff(blk) for blk in b.blocks)
    assert export.export_dst(a) == export.export_dst(b)
    assert [w["code"] for w in b.warnings].count(PUFF_NONE_ELIGIBLE) == 1


def test_puff_rejects_stub_ground():
    planned = [_PPlanned(BAR_A, 20, 0, "G", enclosed_background=True),
               _PPlanned(BAR_B, 21, 1, "B")]
    blocks, warnings, remaining = _run_puff_pass(planned)
    assert [p.shape_id for p in remaining] == ["G"]
    assert [(w["shape_id"], w["reason"]) for w in warnings] == [("G", "not a column shape")]
    assert {r.shape_id for b in blocks for r in b.runs} == {"B"}


def test_puff_satin_never_tatami_even_past_flat_ceiling():
    # 8 mm: the flat pipeline would send it to tatami (> SATIN_MAX_WIDTH_MM).
    blocks, _w, _rem = _run_puff_pass([_PPlanned(box(0, 0, 60, 8), 20, 0, "W")])
    assert blocks[1].step["code"] == "PUFF"
    assert stitches.SATIN in {r.kind for r in blocks[1].runs}
    assert stitches.FILL not in {r.kind for r in blocks[1].runs}
