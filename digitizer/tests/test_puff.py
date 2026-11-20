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
    # The §3.7 inset walk is the underlay's replacement and is tagged
    # underlay-like for the preview; no OTHER run is underlay.
    assert all((r.kind == stitches.UNDERLAY) == (r.role == "puff_under") for r in runs)


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

    def round_ring(runs, ring):
        line = LineString(ring.coords)
        return any(len(r.points) > 3
                   and max(line.distance(Point(p)) for p in r.points) <= 0.3
                   for r in runs)

    # The §3.7 walk (after the stop, in the puff satin) closes the counter...
    walk = [r for r in _puff(RING) if r.role == "puff_under"]
    for ring in (RING.exterior, RING.interiors[0]):
        assert round_ring(walk, ring), "no inset walk round this ring"
    # ...and the pre-stop grip goes round the outer ring only.
    tack = puff_tackdown([RING], ["p"], PipelineConfig(puff=True))
    assert round_ring(tack, RING.exterior)
    assert not round_ring(tack, RING.interiors[0]), "the grip walked a counter"


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
    # The grip is ONE pass round, at its own stitch length.
    assert pts[0] == pts[-1]
    assert len(set(pts)) == len(pts) - 1, "the grip came back over itself"
    assert max(math.dist(a, b) for a, b in zip(pts, pts[1:])) <= machine.PUFF_GRIP_STITCH_MM + 1e-9
    assert len(pts) - 1 <= math.ceil(inset.exterior.length / machine.PUFF_GRIP_STITCH_MM) + 4


@pytest.mark.parametrize("poly", [BAR, RING], ids=["bar", "ring"])
def test_puff_shape_starts_with_inset_walk(poly):
    # §3.7: after the stop, each shape's puff runs open with the inset walk:
    # two passes round every ring, counters included, before caps and satin.
    runs = _puff(poly)
    inset = poly.buffer(-machine.PUFF_INSET_MM, join_style=2)
    rings = [inset.exterior, *inset.interiors]
    walks = []
    for r in runs:
        if r.kind == stitches.TRAVEL:
            continue
        if r.role != "puff_under":
            break
        walks.append(r)
    assert len(walks) == len(rings)
    assert all(r.role != "puff_under" for r in runs[runs.index(walks[-1]) + 1:])
    for r, ring in zip(walks, rings):
        pts = r.points[r.tie_in_pts:]
        # On the inset ring, or on its thinned copy (_WALK_TOLERANCE_MM).
        assert all(ring.distance(Point(p)) <= 0.1 + 1e-6 for p in pts)
        n = len(pts) // 2
        assert len(pts) == 2 * n + 1
        assert pts[0] == pts[n] == pts[-1]
        assert pts[n:] == pts[:n + 1][::-1]
        assert max(math.dist(a, b) for a, b in zip(pts, pts[1:])) <= machine.PUFF_TACKDOWN_STITCH_MM + 1e-9
    # Tied once in, at the walk; no second tie-in at the satin.
    assert runs[0] is walks[0] and runs[0].tie_in_pts == machine.PUFF_TIE_STITCHES
    assert all(r.tie_in_pts == 0 for r in runs[1:] if not r.trim)


@pytest.mark.parametrize("poly", [BAR, RING], ids=["bar", "ring"])
def test_puff_runs_carry_role(poly):
    """Task 9: the preview raises puff by role. Top satin and end-caps are
    "puff"; the inset walk and the pre-stop grip are "puff_under" with an
    underlay-like kind (so they draw subdued); joins stay unroled."""
    from digitizer_core.stage6_puff import puff_tackdown
    runs = _puff(poly)
    sat = [r for r in runs if r.kind == stitches.SATIN]
    assert sat and all(r.role == "puff" for r in sat)
    under = [r for r in runs if r.role == "puff_under"]
    assert under and all(r.kind == stitches.UNDERLAY for r in under)
    assert all(r.role == "" for r in runs if r.kind == stitches.TRAVEL)
    assert all(r.role in ("puff", "puff_under", "") for r in runs)
    tack = puff_tackdown([poly], ["p"], PipelineConfig(puff=True))
    assert tack and all(r.role == "puff_under" and r.kind == stitches.UNDERLAY for r in tack)


def test_puff_roles_reach_the_design(tires_puff):
    from digitizer_core import adapter
    _result, plan = tires_puff
    design = adapter.plan_to_design(plan)
    roles = {s.get("role") for s in design["runs"]}
    assert {"puff", "puff_under"} <= roles


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
    logo_script_tires.png puffs one thread: since R18 every stitched shape of
    it, the i's tittle included (before, the tittle sewed flat)."""
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
    # Before R18 the flat block of the puff thread straight before the puff
    # blocks was the i's tittle; it now puffs with its letter, so TIRES has
    # no flat block left and the design opens on the foam stop.
    # `test_puff_not_merged_with_flat` keeps the same-thread adjacency.
    puff = [b for b in plan.blocks if _is_puff(b)]
    k = plan.blocks.index(puff[0])
    assert all(_is_puff(b) for b in plan.blocks[k:])
    puff_ids = {r.shape_id for b in puff for r in b.runs}
    flat = plan.blocks[:k]
    assert all(b.step is None for b in flat)
    assert not puff_ids & {r.shape_id for b in flat for r in b.runs}


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


# --- Task 5: per-shape override through the shape-layers contract (v1.11) ----

def _edit_region(sid="S1", **meta):
    from digitizer_core.regions import Region
    poly = box(0, 0, 30, 5)
    return Region(shape_id=sid, polygon=poly, thread_index=0, thread_number="1",
                  area_mm2=poly.area, meta={"layer": 0, **meta})


def _apply(overrides, regions=None):
    from digitizer_core.regions import apply_shape_edits
    regions = regions or [_edit_region()]
    out, _t, _w = apply_shape_edits(regions, [0], [], overrides, [])
    return out


def test_puff_override_sets_meta():
    assert _apply({"S1": {"puff": True}})[0].meta["puff"] is True
    assert _apply({"S1": {"puff": False}})[0].meta["puff"] is False
    cleared = _apply({"S1": {"puff": None}}, [_edit_region(puff=True)])
    assert "puff" not in cleared[0].meta


def test_puff_override_rejects_non_bool():
    with pytest.raises(ValueError, match="puff"):
        _apply({"S1": {"puff": "yes"}})


def test_puff_meta_carried():
    from digitizer_core.regions import apply_shape_merges
    a = _edit_region("A", puff=True)
    b = _edit_region("B", puff=True)
    b.polygon = box(30, 0, 60, 5)
    merged, _w = apply_shape_merges([a, b], [["A", "B"]])
    assert len(merged) == 1 and merged[0].meta.get("puff") is True


def test_puff_carried_by_match_shape_ids():
    from digitizer_core.regions import match_shape_ids
    prev = [_edit_region("P1", puff=True)]
    cur = [_edit_region("C1")]
    match_shape_ids(prev, cur)
    assert cur[0].shape_id == "P1" and cur[0].meta.get("puff") is True


def test_puff_kept_on_both_split_pieces():
    from digitizer_core.regions import apply_shape_splits
    r = _edit_region("Q", puff=True)
    pieces, _w = apply_shape_splits([r], {"Q": [[15.0, -20.0], [15.0, 20.0]]})
    assert len(pieces) == 2
    assert all(p.meta.get("puff") is True for p in pieces)


# --- Task 6: steps reach the Design ------------------------------------------

def test_design_steps_only_when_stepped(tires_puff):
    from digitizer_core import adapter
    from digitizer_core.stitches import StitchBlock, StitchPlan, StitchRun
    sq = [(0.0, 0.0), (5.0, 0.0), (5.0, 5.0), (0.0, 5.0)]
    plain = StitchPlan(palette=[], blocks=[
        StitchBlock(0, "1801", (200, 0, 0), [StitchRun(points=sq, kind="run")]),
        StitchBlock(1, "0015", (250, 250, 250), [StitchRun(points=sq, kind="run")]),
    ])
    assert "steps" not in adapter.plan_to_design(plain)

    _result, plan = tires_puff
    design = adapter.plan_to_design(plan)
    steps = design["steps"]
    # R3: one colour per block, in block order, so a step index is a colour row.
    assert len(design["colors"]) == len(plan.blocks) == len(steps)
    by_code = {s["code"]: s["action"] for s in steps}
    assert by_code["PUFF_TACKDOWN"] == "Stop: lay 3 mm puff foam over the outline, then continue"
    # The design ends in puff: the tear-away instruction survives the END rewrite.
    assert steps[-1]["code"] == "PUFF"
    assert steps[-1]["function"] == "end"
    assert steps[-1]["action"] == "Tear away the excess foam. Design complete."


def test_puff_grip_is_a_grip_not_a_walk_tires_114():
    """R14: the pre-stop tack-down is a single-pass grip, not §3.7's two-pass
    walk of every ring. The pro's own "Puff Grip" on TIRES HAT 3D at
    114.3 mm is 279 stitches; the walk-as-tack-down sewed well past that."""
    _result, plan = digitize(TESTDATA / "logo_script_tires.png",
                             cfg(garment_id="hat_front", puff=True, puff_mode="all",
                                 target_width_mm=114.0))
    tack = [b for b in plan.blocks if b.step and b.step["code"] == "PUFF_TACKDOWN"]
    assert tack
    n = sum(len(r.points) for b in tack for r in b.runs)
    assert n < 600, f"PUFF_TACKDOWN sews {n} stitches (the pro's grip is 279)"


# --- R18: the whole letter puffs (a tittle joins its letter's puff) ----------

STEM = box(0, 0, 4, 20)                 # the i's stem: a 4 mm column
DOT = Point(2, 24.5).buffer(2.0, 64)    # its tittle: a 4 mm disc 2.5 mm above


def _puff_ids(blocks):
    return {r.shape_id for b in blocks for r in b.runs}


@pytest.mark.parametrize("mode", ["all", "select"])
def test_letter_dot_joins_its_puffed_letter(mode):
    """Kent 2026-11-19: "If you 3D one part of the letter, the entire letter
    should be 3D." All: the dot is wanted but is no column; select: only the
    stem is ticked. Either way the dot puffs with it, unwarned."""
    planned = [_PPlanned(STEM, 20, 0, "STEM", puff=True), _PPlanned(DOT, 20, 1, "DOT")]
    blocks, warnings, remaining = _run_puff_pass(planned, puff_mode=mode)
    assert _puff_ids(blocks) == {"STEM", "DOT"}
    assert remaining == []
    assert not [w for w in warnings if w.get("shape_id") == "DOT"]


def test_letter_dot_never_spreads_without_a_puffed_letter():
    # Select with nothing ticked: the dot does not puff on its own.
    planned = [_PPlanned(STEM, 20, 0, "STEM"), _PPlanned(DOT, 20, 1, "DOT")]
    blocks, _w, remaining = _run_puff_pass(planned, puff_mode="select")
    assert blocks == [] and len(remaining) == 2


def test_letter_dot_other_thread_or_far_stays_flat():
    far = Point(2, 40).buffer(2.0, 64)   # 18 mm away: some other mark
    planned = [_PPlanned(STEM, 20, 0, "STEM", puff=True),
               _PPlanned(DOT, 21, 1, "DOT"),        # another thread
               _PPlanned(far, 20, 2, "FAR")]
    blocks, _w, remaining = _run_puff_pass(planned, puff_mode="select")
    assert _puff_ids(blocks) == {"STEM"}
    assert {p.shape_id for p in remaining} == {"DOT", "FAR"}


def test_letter_spread_never_pulls_in_the_background():
    """A compact ground piece beside the letter (stage 4's
    `enclosed_background`) never joins, and a ground nearer the dot than
    its letter is not taken for the dot's neighbour."""
    ground_dot = Point(-4, 10).buffer(2.0, 64)
    ground = box(-30, -30, 30, 50).difference(STEM.buffer(0.5)).difference(DOT.buffer(0.5))
    planned = [_PPlanned(STEM, 20, 0, "STEM", puff=True),
               _PPlanned(DOT, 20, 1, "DOT"),
               _PPlanned(ground_dot, 20, 2, "GDOT", enclosed_background=True),
               _PPlanned(ground, 20, 3, "G", enclosed_background=True)]
    for mode in ("all", "select"):
        blocks, _w, _rem = _run_puff_pass(planned, puff_mode=mode)
        assert _puff_ids(blocks) == {"STEM", "DOT"}


def test_letter_dot_out_of_band_stays_flat_with_reason():
    tiny = Point(2, 22).buffer(1.0, 64)   # a 2 mm dot: too thin for foam
    planned = [_PPlanned(STEM, 20, 0, "STEM", puff=True), _PPlanned(tiny, 20, 1, "TINY")]
    blocks, warnings, remaining = _run_puff_pass(planned, puff_mode="select")
    assert _puff_ids(blocks) == {"STEM"}
    assert [p.shape_id for p in remaining] == ["TINY"]
    hit = [w for w in warnings if w["code"] == PUFF_SHAPE_INELIGIBLE]
    assert [w["shape_id"] for w in hit] == ["TINY"]
    assert hit[0]["reason"].startswith("too thin for foam (2.0")


DISC = Point(0, 0).buffer(2.0, 128)   # a 4 mm round dot


def test_puff_compact_shape_closes_the_disc():
    from digitizer_core.stage6_puff import puff_compact_shape
    runs = puff_compact_shape(DISC, "d", PipelineConfig(puff=True))
    assert runs
    # Coverage from the raised runs alone: the walk is inset, so it can't
    # be what closes the edge.
    top = [p for r in runs if r.role == "puff" for p in r.points]
    assert _covered(DISC.exterior, top) >= 0.8
    assert all((r.kind == stitches.UNDERLAY) == (r.role == "puff_under") for r in runs)
    assert any(r.kind == stitches.SATIN for r in runs)
    n = machine.PUFF_TIE_STITCHES
    assert runs[0].tie_in_pts == n
    assert _bounce(runs[0].points[:n + 1]) and _bounce(runs[-1].points[-(n + 1):])
    # Every penetration lands inside the dot (no foam cut outside the art).
    grown = DISC.buffer(0.01)
    assert all(grown.contains(Point(p)) for r in runs for p in r.points)


def test_tires_i_dot_puffs_with_its_letter():
    """End to end at the pro's 114 mm: the i's tittle (the small round
    shape) sews inside a PUFF block and no PUFF_SHAPE_INELIGIBLE names it."""
    from digitizer_core.stage6_puff import _max_inscribed_diameter_mm
    result, plan = digitize(TESTDATA / "logo_script_tires.png",
                            cfg(garment_id="hat_front", puff=True, puff_mode="all",
                                target_width_mm=114.0))
    dots = [r for r in result.regions if not r.meta.get("enclosed_background")
            and r.polygon.area < 40
            and r.polygon.area < 1.5 * math.pi * (_max_inscribed_diameter_mm(r.polygon) / 2) ** 2]
    assert len(dots) == 1, [r.shape_id for r in dots]
    sid = dots[0].shape_id
    puff = {r.shape_id for b in plan.blocks if b.step and b.step["code"] == "PUFF" for r in b.runs}
    assert sid in puff
    assert not [w for w in plan.warnings
                if w["code"] == PUFF_SHAPE_INELIGIBLE and w.get("shape_id") == sid]


def test_ticking_only_the_dot_puffs_its_letter():
    """R18 is symmetric: in select, ticking the tittle alone puffs its host
    letter shape and the tittle with it -- over the host's own
    `puff: False`, since the letter is one decision."""
    for stem_meta in ({}, {"puff": False}):
        planned = [_PPlanned(STEM, 20, 0, "STEM", **stem_meta),
                   _PPlanned(DOT, 20, 1, "DOT", puff=True)]
        blocks, warnings, remaining = _run_puff_pass(planned, puff_mode="select")
        assert _puff_ids(blocks) == {"STEM", "DOT"}
        assert remaining == [] and warnings == []


def test_ticking_the_dot_of_an_unpuffable_letter_leaves_both_flat():
    thin = box(1, 0, 3, 20)               # a 2 mm stem: too thin for foam
    dot = Point(2, 22.5).buffer(2.0, 64)
    planned = [_PPlanned(thin, 20, 0, "STEM"), _PPlanned(dot, 20, 1, "DOT", puff=True)]
    blocks, warnings, remaining = _run_puff_pass(planned, puff_mode="select")
    assert blocks == []
    assert {p.shape_id for p in remaining} == {"STEM", "DOT"}
    hits = [w for w in warnings if w["code"] == PUFF_SHAPE_INELIGIBLE]
    assert len(hits) == 1 and hits[0]["shape_id"] == "DOT"
    assert hits[0]["reason"].startswith("its letter can't be puffed: too thin for foam")


# --- R18 review fixes: no chaining, placement guard ------------------------

@pytest.mark.parametrize("layout", ["beside", "above"])
def test_letter_spread_never_chains_along_a_row_of_dots(layout):
    """A row of five dots never walks dot-to-dot into the puff: at most the
    nearest joins (beside the stem, none -- a dot beside is no tittle)."""
    if layout == "beside":
        dots = [Point(6.5 + 5.5 * k, 10).buffer(2.0, 64) for k in range(5)]
    else:
        # 3 mm apart, so D0's nearest is the stem (2.5 mm), not D1.
        dots = [Point(2, 24.5 + 7.0 * k).buffer(2.0, 64) for k in range(5)]
    planned = [_PPlanned(STEM, 20, 0, "STEM", puff=True)] + [
        _PPlanned(d, 20, k + 1, f"D{k}") for k, d in enumerate(dots)]
    for mode in ("all", "select"):
        blocks, _w, _rem = _run_puff_pass(planned, puff_mode=mode)
        joined = _puff_ids(blocks) - {"STEM"}
        assert joined <= {"D0"}, (mode, layout, joined)
        if layout == "above":
            assert joined == {"D0"}


def test_umlaut_second_dot_joins_through_the_first():
    u = box(0, 0, 12, 4)                       # a stand-in letter body
    d1 = Point(3, 7).buffer(2.0, 64)
    d2 = Point(8.5, 7).buffer(2.0, 64)         # nearest the first dot
    planned = [_PPlanned(u, 20, 0, "U", puff=True),
               _PPlanned(d1, 20, 1, "D1"), _PPlanned(d2, 20, 2, "D2")]
    blocks, _w, _rem = _run_puff_pass(planned, puff_mode="select")
    assert _puff_ids(blocks) == {"U", "D1", "D2"}


PERIOD = Point(7, 2).buffer(2.0, 64)    # just right of the stem's foot


def test_period_beside_a_letter_does_not_join():
    planned = [_PPlanned(STEM, 20, 0, "STEM"), _PPlanned(PERIOD, 20, 1, "DOT")]
    blocks, _w, remaining = _run_puff_pass(planned, puff_mode="all")
    assert _puff_ids(blocks) == {"STEM"}
    planned = [_PPlanned(STEM, 20, 0, "STEM"), _PPlanned(PERIOD, 20, 1, "DOT", puff=True)]
    blocks, _w, remaining = _run_puff_pass(planned, puff_mode="select")
    assert blocks == []


def test_letter_part_other_text_cluster_does_not_join():
    planned = [_PPlanned(STEM, 20, 0, "STEM", puff=True, text_cluster_id="T1"),
               _PPlanned(DOT, 20, 1, "DOT", text_cluster_id="T2")]
    blocks, _w, _rem = _run_puff_pass(planned, puff_mode="select")
    assert _puff_ids(blocks) == {"STEM"}


def test_dot_of_a_wanted_unpuffable_letter_names_the_letter():
    thin = box(1, 0, 3, 20)
    dot = Point(2, 22.5).buffer(2.0, 64)
    planned = [_PPlanned(thin, 20, 0, "STEM"), _PPlanned(dot, 20, 1, "DOT")]
    _b, warnings, _rem = _run_puff_pass(planned, puff_mode="all")
    why = {w["shape_id"]: w["reason"] for w in warnings if w["code"] == PUFF_SHAPE_INELIGIBLE}
    assert why["DOT"].startswith("its letter can't be puffed: too thin for foam")
