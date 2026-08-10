"""The shape-layers contract v1: deletions and per-shape overrides.

The review screen edits shapes by the content-derived ids the payload reports;
a re-digitize sends `deleted_shape_ids` and `shape_overrides` back through the
same stateless config the whole service runs on. What this file pins, in order
of what it would cost the shop if it broke:

- the NO-OP is byte-identical to the shipped engine (the goldens survive);
- a deletion removes exactly that geometry, says so, and never errors on an id
  the art no longer contains;
- a recolor sews the shape in the right color BLOCK, not just the right RGB;
- a forced tier actually changes the emitted run kinds;
- a per-shape fill angle beats the global one;
- a layer override moves the shape's sew position;
- and the two fields participate in the job cache key, or an edited
  re-digitize would return the stale cached job.
"""
from __future__ import annotations

import hashlib
import math
from collections import Counter

import pytest
from shapely import affinity
from shapely.geometry import Polygon

from digitizer_core import PipelineConfig, get_fabric, plan_stitches, run_stages
from digitizer_core.export import export_dst
from digitizer_core.pipeline import digitize
from digitizer_core.regions import Region, apply_shape_edits, match_shape_ids
from digitizer_core.stage5_overlap import resolve_overlaps
from digitizer_core.stage7_sequence import sequence

from .conftest import TESTDATA, cfg
from .test_pushcomp import GOLDEN_FLAG_OFF

ART = TESTDATA / "logo_whitebg.png"
FAB = get_fabric("pique_knit")


# --- helpers ----------------------------------------------------------------

def only(result, thread_number: str) -> Region:
    """The one region sewing `thread_number` (asserts uniqueness)."""
    rs = [r for r in result.regions if r.thread_number == thread_number]
    assert len(rs) == 1, f"expected one {thread_number} region, got {len(rs)}"
    return rs[0]


def kinds_by_shape(plan) -> dict[str, Counter]:
    out: dict[str, Counter] = {}
    for b in plan.blocks:
        for r in b.runs:
            out.setdefault(r.shape_id, Counter())[r.kind] += len(r.points)
    return out


def sew_rank(plan) -> dict[str, tuple[int, int]]:
    """shape_id -> (block index, first-sewn rank)."""
    order: dict[str, tuple[int, int]] = {}
    for bi, b in enumerate(plan.blocks):
        for r in b.runs:
            if r.shape_id and r.shape_id not in order:
                order[r.shape_id] = (bi, len(order))
    return order


def axis_lengths(plan, shape_id: str) -> tuple[float, float]:
    """Total fill-segment length near 0 deg and near 90 deg for one shape."""
    h = v = 0.0
    for b in plan.blocks:
        for r in b.runs:
            if r.shape_id != shape_id or r.kind != "fill":
                continue
            for a, c in zip(r.points, r.points[1:]):
                d = math.dist(a, c)
                ang = math.degrees(math.atan2(c[1] - a[1], c[0] - a[0])) % 180.0
                if min(ang, 180.0 - ang) < 20.0:
                    h += d
                elif abs(ang - 90.0) < 20.0:
                    v += d
    return h, v


def bar(w: float, h: float, cx: float = 0.0) -> Polygon:
    p = Polygon([(0, 0), (w, 0), (w, h), (0, h)])
    return affinity.translate(p, cx - w / 2, -h / 2)


def region(poly: Polygon, sid: str, meta: dict | None = None) -> Region:
    m = {"layer": 0}
    m.update(meta or {})
    return Region(shape_id=sid, polygon=poly, thread_index=0,
                  thread_number="1000", area_mm2=poly.area, meta=m)


def plan_for(regions: list[Region], **cfg_kw):
    c = PipelineConfig(**cfg_kw)
    planned, _ = resolve_overlaps(regions, FAB, c)
    blocks, warnings = sequence(planned, FAB, c)
    class _P:  # just enough plan for the helpers above
        pass
    p = _P()
    p.blocks = blocks
    return p, warnings


# --- the edited round-trip fixture ------------------------------------------

@pytest.fixture(scope="module")
def base():
    return digitize(ART, cfg())


@pytest.fixture(scope="module")
def edited(base):
    """One re-digitize carrying every edit kind at once, plus two stale ids.

    Shapes are found by thread, not by hard-coded id, so the fixture survives
    an id-scheme change without silently testing nothing.
    """
    result, _plan = base
    red = only(result, "1704")       # big filled circle
    blue = only(result, "3902")      # ring
    green = only(result, "5510")     # thin bar — the design's one satin shape
    purple = only(result, "2905")    # rectangle, the only 2905 shape
    orange = [r for r in result.regions if r.thread_number == "1305"]
    tiny = min(orange, key=lambda r: r.area_mm2)     # the run-tier satellite
    big_orange = max(orange, key=lambda r: r.area_mm2)  # the surviving 1305 shape

    c = cfg(
        deleted_shape_ids=[tiny.shape_id, "SNOPE"],
        shape_overrides={
            # recolor + underlay style on the same shape: two edits, one
            # override entry, exactly what a real review-screen edit looks
            # like once a shape has more than one field touched.
            purple.shape_id: {"thread_index": red.thread_index, "underlay_style": "none"},
            green.shape_id: {"tier": "fill"},                     # tier flip
            red.shape_id: {"fill_angle_deg": 90.0},               # angle
            blue.shape_id: {"layer": 99},                         # sew last
            big_orange.shape_id: {"sew_order": 0},                # within-layer order
            "SNOPE2": {"tier": "satin"},                          # stale
            "SNOPE3": {"sew_order": 3},                           # stale
            "SNOPE4": {"underlay_style": "zigzag"},               # stale
        },
    )
    result2, plan2 = digitize(ART, c)
    return {
        "result": result2, "plan": plan2,
        "red": red, "blue": blue, "green": green, "purple": purple,
        "tiny": tiny, "big_orange": big_orange,
    }


# --- the no-op golden --------------------------------------------------------

def test_noop_edits_are_byte_identical_to_the_shipped_engine():
    """Empty deletions + empty overrides, explicitly present, must reproduce
    the committed pre-contract golden to the byte — full point stream via the
    DST writer, not counts. The hash is test_pushcomp's pinned baseline."""
    noop = dict(deleted_shape_ids=[], shape_overrides={})
    stages = run_stages(ART, cfg(**noop))
    plan = plan_stitches(stages, cfg(garment_id="left_chest", **noop))
    blob = export_dst(plan)
    want_hash, want_n, want_bytes = GOLDEN_FLAG_OFF[("logo_whitebg.png", "left_chest")]
    got_n = sum(len(r.points) for b in plan.blocks for r in b.runs)
    assert (hashlib.sha256(blob).hexdigest()[:20], got_n, len(blob)) == \
        (want_hash, want_n, want_bytes)


# --- deletion ----------------------------------------------------------------

def test_delete_removes_exactly_that_shape_and_warns(base, edited):
    result, _ = base
    r2 = edited["result"]
    tiny = edited["tiny"]

    assert {r.shape_id for r in r2.regions} == \
        {r.shape_id for r in result.regions} - {tiny.shape_id}
    # Stage 1-4 geometry of the survivors is untouched: same ids, same areas.
    base_area = {r.shape_id: round(r.area_mm2, 6) for r in result.regions}
    assert all(round(r.area_mm2, 6) == base_area[r.shape_id] for r in r2.regions)
    # And not a single emitted stitch belongs to the deleted shape.
    assert tiny.shape_id not in kinds_by_shape(edited["plan"])

    w = next(w for w in r2.warnings if w["code"] == "SHAPES_DELETED_BY_USER")
    assert w["count"] == 1 and w["ids"] == [tiny.shape_id]


def test_unknown_ids_warn_and_never_error(edited):
    w = next(w for w in edited["result"].warnings
             if w["code"] == "SHAPE_EDIT_UNKNOWN_ID")
    assert w["count"] == 4 and w["ids"] == ["SNOPE", "SNOPE2", "SNOPE3", "SNOPE4"]


# --- recolor -----------------------------------------------------------------

def test_recolor_moves_the_shape_to_the_right_color_block(base, edited):
    plan2 = edited["plan"]
    purple, red = edited["purple"], edited["red"]

    r = next(r for r in edited["result"].regions if r.shape_id == purple.shape_id)
    assert (r.thread_index, r.thread_number) == (red.thread_index, "1704")

    order = sew_rank(plan2)
    p_block, _ = order[purple.shape_id]
    r_block, _ = order[red.shape_id]
    assert p_block == r_block, "recolored shape must sew inside 1704's block"
    assert plan2.blocks[p_block].thread_number == "1704"


def test_recolor_that_empties_a_thread_drops_its_cone_from_the_palette(base, edited):
    numbers = [p["number"] for p in edited["result"].palette]
    assert "2905" not in numbers, "nothing sews 2905 any more"
    assert "1305" in numbers, "1305 still has its big rectangle"
    base_numbers = [p["number"] for p in base[0].palette]
    assert [n for n in base_numbers if n != "2905"] == numbers


# --- tier --------------------------------------------------------------------

def test_tier_flip_changes_what_the_machine_sews(base, edited):
    green = edited["green"].shape_id
    before = kinds_by_shape(base[1])[green]
    after = kinds_by_shape(edited["plan"])[green]
    assert before["satin"] > 0 and before["fill"] == 0
    assert after["fill"] > 0 and after["satin"] == 0


def test_forced_satin_on_a_fill_classified_shape():
    # 20x8: ribbon width 5.7 mm, rejected by the classifier, but the skeleton
    # resolves fine — exactly the shape a digitizer overrules the machine on.
    auto, _ = plan_for([region(bar(20, 8), "X")])
    forced, _ = plan_for([region(bar(20, 8), "X", {"tier": "satin"})])
    assert kinds_by_shape(auto)["X"]["fill"] > 0
    assert kinds_by_shape(auto)["X"]["satin"] == 0
    assert kinds_by_shape(forced)["X"]["satin"] > 0
    assert kinds_by_shape(forced)["X"]["fill"] == 0


def test_forced_fill_and_run_on_a_satin_classified_shape():
    thin = bar(30, 2.2)   # a ribbon: auto is satin
    auto, _ = plan_for([region(thin, "T")])
    assert kinds_by_shape(auto)["T"]["satin"] > 0

    fill, _ = plan_for([region(thin, "T", {"tier": "fill"})])
    k = kinds_by_shape(fill)["T"]
    assert k["fill"] > 0 and k["satin"] == 0

    run, _ = plan_for([region(thin, "T", {"tier": "run"})])
    k = kinds_by_shape(run)["T"]
    assert k["run"] > 0 and k["satin"] == 0 and k["fill"] == 0


# --- fill angle --------------------------------------------------------------

def test_per_shape_fill_angle_beats_the_global():
    a, b = bar(12, 12, cx=-10), bar(12, 12, cx=10)
    plan, _ = plan_for(
        [region(a, "A", {"fill_angle_deg": 90.0}), region(b, "B")],
        fill_angle_deg=0.0,
    )
    ah, av = axis_lengths(plan, "A")
    bh, bv = axis_lengths(plan, "B")
    assert av > 10 * ah, "A's rows must run along its own 90, not the global 0"
    assert bh > 10 * bv, "B keeps the global angle"


def test_the_config_override_reaches_the_needle(edited):
    """Chain of custody: cfg.shape_overrides -> Region.meta -> emitted rows.
    The red circle's PCA angle is nowhere near vertical, so vertical rows can
    only have come from the override."""
    red = edited["red"].shape_id
    r = next(r for r in edited["result"].regions if r.shape_id == red)
    assert r.meta.get("fill_angle_deg") == 90.0
    h, v = axis_lengths(edited["plan"], red)
    assert v > 5 * h


# --- layer -------------------------------------------------------------------

def test_layer_override_changes_sew_order(base, edited):
    blue = edited["blue"].shape_id
    assert sew_rank(base[1])[blue][0] == 1, "baseline: 3902 sews second"
    order = sew_rank(edited["plan"])
    b_block, _ = order[blue]
    assert b_block == len(edited["plan"].blocks) - 1, "layer 99 sews last"
    assert edited["plan"].blocks[b_block].thread_number == "3902"
    # The palette still lists 3902 — moving a shape never drops its cone.
    assert "3902" in [p["number"] for p in edited["result"].palette]


# --- sew_order (within-layer order, contract v1.2) ---------------------------
#
# Distinct from `layer` above: `layer` picks WHICH color block a shape sews
# in; `sew_order` picks WHERE within that block's own nearest-neighbour
# sequence. Both live on Region.meta and both flow through the same
# apply_shape_edits / SHAPE_EDIT_UNKNOWN_ID machinery, but sew_order is
# resolved one stage later, inside stage 7's own picking loop.

def test_the_sew_order_config_override_reaches_the_needle(edited):
    big_orange = edited["big_orange"].shape_id
    r = next(r for r in edited["result"].regions if r.shape_id == big_orange)
    assert r.meta.get("sew_order") == 0


def test_sew_order_forces_explicit_position_within_layer():
    """Three same-layer bars naturally sweep left, middle, right — nearest-
    neighbour never backtracks over ground it is already standing on.
    Pinning the RIGHT bar to slot 0 must reverse the whole order: not just
    relabel it first, but actually route the middle bar's entry from
    wherever the right bar's real stitching ended, same as the layer
    override already proves for block order."""
    left, middle, right = bar(8, 8, cx=-20), bar(8, 8, cx=0), bar(8, 8, cx=20)

    auto, _ = plan_for([region(left, "L"), region(middle, "M"), region(right, "R")])
    order_auto = sorted(sew_rank(auto), key=lambda sid: sew_rank(auto)[sid][1])
    assert order_auto == ["L", "M", "R"], "baseline: nearest-neighbour sweeps left to right"

    pinned, _ = plan_for([
        region(left, "L"), region(middle, "M"),
        region(right, "R", {"sew_order": 0}),
    ])
    order_pinned = sorted(sew_rank(pinned), key=lambda sid: sew_rank(pinned)[sid][1])
    assert order_pinned == ["R", "M", "L"], \
        "R is forced first; M and L still resolve by nearest-neighbour from there"


def test_sew_order_falls_back_to_nearest_neighbour_for_unpinned_shapes():
    """Pinning ONE shape to a late slot must not disturb how the UNPINNED
    shapes are chosen relative to each other — they still compete for every
    slot nearest-neighbour would have given them, exactly the fallback the
    contract promises."""
    left, middle, right = bar(8, 8, cx=-20), bar(8, 8, cx=0), bar(8, 8, cx=20)

    pinned, _ = plan_for([
        region(left, "L"), region(middle, "M", {"sew_order": 2}), region(right, "R"),
    ])
    order = sorted(sew_rank(pinned), key=lambda sid: sew_rank(pinned)[sid][1])
    assert order == ["L", "R", "M"], \
        "M is deferred to last; L and R still sew in nearest-neighbour order"


def test_sew_order_absent_layer_is_untouched():
    """No shape in the layer carries an override: byte-identical to the
    pre-feature picking loop (same three shapes, no meta key at all)."""
    left, middle, right = bar(8, 8, cx=-20), bar(8, 8, cx=0), bar(8, 8, cx=20)
    plan, _ = plan_for([region(left, "L"), region(middle, "M"), region(right, "R")])
    order = sorted(sew_rank(plan), key=lambda sid: sew_rank(plan)[sid][1])
    assert order == ["L", "M", "R"]


# --- border strings ----------------------------------------------------------

def test_border_override_strings_beat_the_global_mode():
    sq = bar(12, 12)
    on, _ = plan_for([region(sq, "Q", {"border": "bean"})])       # global off
    off, _ = plan_for([region(sq, "Q", {"border": "off"})], border="auto")
    auto, _ = plan_for([region(sq, "Q", {"border": "auto"})])     # global off
    assert kinds_by_shape(on)["Q"]["bean"] > 0
    k_off = kinds_by_shape(off)["Q"]
    assert k_off["border"] == 0 and k_off["bean"] == 0
    assert kinds_by_shape(auto)["Q"]["border"] > 0


# --- underlay style ----------------------------------------------------------
#
# Fill-classified shapes only: a 30x30 square is well past satin's default
# max width (3.0 mm), so `plan_for` always routes it through `stitch_shape`,
# the tatami emitter `underlay_style` (via `eff_underlay_style`) actually
# reaches.

def test_underlay_style_override_changes_emitted_underlay_geometry():
    sq = bar(30, 30)
    auto, _ = plan_for([region(sq, "Q")])              # pique_knit -> edge_lattice
    off, _ = plan_for([region(sq, "Q", {"underlay_style": "none"})])
    on, _ = plan_for([region(sq, "Q", {"underlay_style": "zigzag"})])
    assert kinds_by_shape(auto)["Q"]["underlay"] > 0, "fabric default sews underlay"
    assert kinds_by_shape(off)["Q"]["underlay"] == 0, "an explicit none sews none"
    assert kinds_by_shape(on)["Q"]["underlay"] > 0
    # And it is not just present/absent — a different named style is a
    # different stitch count, not a coincidence of the same geometry.
    assert kinds_by_shape(auto)["Q"]["underlay"] != kinds_by_shape(on)["Q"]["underlay"]


def test_underlay_style_override_beats_the_global_config_in_both_directions():
    sq = bar(30, 30)
    # Global underlay is OFF design-wide; the per-shape style still wins.
    on, _ = plan_for([region(sq, "Q", {"underlay_style": "zigzag"})], underlay=False)
    # Global underlay style is zigzag; the per-shape "none" still wins.
    off, _ = plan_for([region(sq, "Q", {"underlay_style": "none"})], underlay_style="zigzag")
    # No override at all: inherits whatever the global config says.
    inherited, _ = plan_for([region(sq, "Q")], underlay_style="edge_run")
    assert kinds_by_shape(on)["Q"]["underlay"] > 0
    assert kinds_by_shape(off)["Q"]["underlay"] == 0
    assert kinds_by_shape(inherited)["Q"]["underlay"] > 0


def test_underlay_style_reaches_the_contour_tier_too():
    """Same override, same precedence, when the design-wide fill technique is
    contour instead of tatami — `eff_underlay_style` feeds both call sites."""
    sq = bar(30, 30)
    off, _ = plan_for([region(sq, "Q", {"underlay_style": "none"})],
                      fill_technique="contour")
    on, _ = plan_for([region(sq, "Q", {"underlay_style": "zigzag"})],
                     fill_technique="contour")
    assert kinds_by_shape(off)["Q"]["underlay"] == 0
    assert kinds_by_shape(on)["Q"]["underlay"] > 0


def test_underlay_style_override_does_not_reach_satin():
    """Satin keeps its own fabric-preset underlay knob — the shape-override
    field is documented (config.py) as fill/contour only, and this pins that
    a satin-classified shape's underlay is unaffected by it."""
    ribbon = bar(30, 2.2)     # narrow enough to classify as satin
    plain, _ = plan_for([region(ribbon, "T")])
    overridden, _ = plan_for([region(ribbon, "T", {"underlay_style": "none"})])
    assert kinds_by_shape(plain)["T"]["satin"] > 0
    assert kinds_by_shape(overridden)["T"]["satin"] > 0
    # Satin's own underlay (spine center-run) is fabric-driven either way —
    # the override changed nothing about it.
    assert kinds_by_shape(plain)["T"]["underlay"] == kinds_by_shape(overridden)["T"]["underlay"]


def test_underlay_style_override_rejects_an_unknown_style():
    """Core-level defense in depth, same as `tier`/`border`'s own ValueError:
    the service's own vocabulary check (test_service.py) is the first line,
    but `apply_shape_edits` enforces it independently for any other caller."""
    regs = [region(bar(12, 12), "Q")]
    with pytest.raises(ValueError):
        apply_shape_edits(regs, [0], [], {"Q": {"underlay_style": "sparkly"}}, chart=[0] * 20)


# --- boundary override (contract v1.4) ---------------------------------------
#
# Higher risk than every other key in this file: a hand-edited outline can be
# self-intersecting, degenerate, or poke a hole outside the new shell, any of
# which would corrupt stage 5 onward if it reached there. What this section
# pins: a valid reshape replaces the polygon (and its cached area) exactly,
# holes ride along unchanged, downstream stitch planning stays sane on an
# awkward-but-valid hand edit, and every one of the invalid shapes above is
# rejected with a clear ValueError — never a crash, never silently repaired.

def _no_degenerate_stitches(plan) -> None:
    """Every run: finite coordinates, no zero-length segment (a stitch that
    goes nowhere), which is what a self-intersecting or near-degenerate fill
    would produce if the boundary validation let one through."""
    for b in plan.blocks:
        for r in b.runs:
            assert r.points, f"{r.kind} run with no points"
            for x, y in r.points:
                assert math.isfinite(x) and math.isfinite(y)
            for a, c in zip(r.points, r.points[1:]):
                assert a != c, f"zero-length stitch in a {r.kind} run"


def test_boundary_override_replaces_the_polygon_and_recomputes_area():
    """The reshaped geometry — not just a bigger bounding box — reaches the
    Region, and `area_mm2` (which sort order and the review payload both
    depend on) is recomputed from it, not left stale."""
    sq = bar(10, 10)
    # An L-shape: a real reshape, not just a scale.
    l_shape = [[-5, -5], [5, -5], [5, 0], [0, 0], [0, 5], [-5, 5]]
    regs, _, warns = apply_shape_edits(
        [region(sq, "Q")], [0], [], {"Q": {"boundary_override": l_shape}}, chart=[0] * 20,
    )
    assert warns == []
    got = regs[0]
    assert got.polygon.equals(Polygon(l_shape))
    assert got.area_mm2 == pytest.approx(75.0)   # 100 - the missing 5x5 corner
    assert got.area_mm2 != sq.area                # actually changed, not stale


def test_boundary_override_preserves_existing_holes():
    """Boundary editing is exterior-ring only (v1.4 scope) — a shape's holes
    (e.g. a letter's counter) ride forward unchanged onto the new shell."""
    shell = [(0, 0), (10, 0), (10, 10), (0, 10)]
    hole = [(4, 4), (6, 4), (6, 6), (4, 6)]
    ring = region(Polygon(shell, [hole]), "O")
    bigger_shell = [[0, 0], [12, 0], [12, 12], [0, 12]]
    regs, _, _ = apply_shape_edits(
        [ring], [0], [], {"O": {"boundary_override": bigger_shell}}, chart=[0] * 20,
    )
    poly = regs[0].polygon
    assert len(poly.interiors) == 1
    assert poly.area == pytest.approx(144.0 - 4.0)   # bigger shell, same 2x2 hole


def test_boundary_override_survives_through_stage5_and_stage7_on_an_awkward_shape():
    """The downstream-safety check: a valid but deliberately awkward hand
    edit (a deep, near-touching notch — the kind a real drag-vertex UI would
    produce) must still resolve overlaps and sequence into sane stitches,
    alongside an ordinary neighbour shape of a different colour."""
    sq = bar(20, 20)
    awkward = [
        [-10, -10], [10, -10], [10, 10], [0.2, 10], [0.2, -9.5], [-0.2, -9.5],
        [-0.2, 10], [-10, 10],
    ]
    assert Polygon(awkward).is_valid, "fixture must itself be a valid polygon"
    regs, _, warns = apply_shape_edits(
        [region(sq, "Q")], [0], [], {"Q": {"boundary_override": awkward}}, chart=[0] * 20,
    )
    assert warns == []
    neighbour = region(bar(10, 10, cx=25), "N", {})
    plan, seq_warnings = plan_for(regs + [neighbour])
    _no_degenerate_stitches(plan)
    assert kinds_by_shape(plan)["Q"], "the reshaped region still produced stitches"
    assert kinds_by_shape(plan)["N"], "and its neighbour is unaffected"


@pytest.mark.parametrize("bad_boundary,reason", [
    ([[0, 0], [10, 10], [10, 0], [0, 10]], "self-intersecting bowtie"),
    ([[0, 0], [0.1, 0], [0.1, 0.1], [0, 0.1]], "area under the sewability floor"),
    ([[0, 0], [1, 1]], "fewer than 3 points"),
])
def test_boundary_override_rejects_bad_geometry_with_a_clear_error_not_a_crash(bad_boundary, reason):
    regs = [region(bar(12, 12), "Q")]
    with pytest.raises(ValueError, match=r"boundary_override"):
        apply_shape_edits(regs, [0], [], {"Q": {"boundary_override": bad_boundary}}, chart=[0] * 20)
    # And the input regions were never mutated by the failed attempt.
    assert regs[0].polygon.equals(bar(12, 12))


def test_boundary_override_rejects_too_many_points():
    from digitizer_core.regions import _MAX_BOUNDARY_POINTS

    huge = [[math.cos(t) * 10, math.sin(t) * 10]
            for t in [i * 2 * math.pi / (_MAX_BOUNDARY_POINTS + 1)
                      for i in range(_MAX_BOUNDARY_POINTS + 1)]]
    regs = [region(bar(12, 12), "Q")]
    with pytest.raises(ValueError, match="boundary_override"):
        apply_shape_edits(regs, [0], [], {"Q": {"boundary_override": huge}}, chart=[0] * 20)


def test_boundary_override_dedupes_a_closed_ring_the_same_as_outline_mm_sends_it():
    """`outline_mm` (the review payload) always repeats the first point as the
    last — shapely's own `exterior.coords` convention, and the natural shape
    for a client to read handles from and send straight back. That must not
    be mistaken for an extra, distinct point."""
    sq = [[0, 0], [10, 0], [10, 10], [0, 10], [0, 0]]   # closed, 5 entries
    regs, _, warns = apply_shape_edits(
        [region(bar(10, 10), "Q")], [0], [], {"Q": {"boundary_override": sq}}, chart=[0] * 20,
    )
    assert warns == []
    assert regs[0].polygon.equals(Polygon(sq))
    assert regs[0].meta["boundary_override"] == [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0)]


# --- carry-forward -----------------------------------------------------------

def test_review_intent_rides_the_id_carry_forward():
    """`match_shape_ids` carries the operator's per-shape decisions onto the
    next generation, exactly as the config docstring promises for border and
    appliqué — and now for tier, fill angle, within-layer sew order,
    underlay style and a hand-edited boundary too."""
    prev = [region(bar(10, 4), "OLD",
                   {"tier": "satin", "fill_angle_deg": 45.0, "border": "bean",
                    "applique": True, "layer": 3, "sew_order": 1,
                    "underlay_style": "zigzag",
                    "boundary_override": [(-5.0, -2.0), (5.0, -2.0), (5.0, 2.0), (-5.0, 2.0)]})]
    cur = [region(bar(10.2, 4.1), "NEW")]
    match_shape_ids(prev, cur)
    assert cur[0].shape_id == "OLD"
    assert cur[0].meta.get("tier") == "satin"
    assert cur[0].meta.get("fill_angle_deg") == 45.0
    assert cur[0].meta.get("border") == "bean"
    assert cur[0].meta.get("applique") is True
    assert cur[0].meta.get("sew_order") == 1
    assert cur[0].meta.get("underlay_style") == "zigzag"
    assert cur[0].meta.get("boundary_override") == \
        [(-5.0, -2.0), (5.0, -2.0), (5.0, 2.0), (-5.0, 2.0)]
    assert cur[0].meta["layer"] == 0, "pipeline facts stay the new generation's"


def test_boundary_override_survives_a_stateless_redigitize_keyed_by_the_stable_shape_id(base):
    """The same guarantee the other override keys have, proven the same way:
    `apply_shape_edits` runs on FRESH stage 1-4 output every generation, so
    the id a `boundary_override` is keyed on is the deterministic pre-edit
    hash (`assign_shape_ids`) — stable across re-digitizes of the same
    artwork/config regardless of how drastically the edit reshapes the
    survivor. This is the mechanism `match_shape_ids`' carry-forward (above)
    exists to backstop if that hash ever churns; this test proves the common
    path that doesn't need it."""
    result, _ = base
    purple = only(result, "2905")     # rectangle
    grown = [[x * 1.5, y * 1.5] for x, y in purple.polygon.exterior.coords]

    c = cfg(shape_overrides={purple.shape_id: {"boundary_override": grown}})
    result2, plan2 = digitize(ART, c)

    survivor = next(r for r in result2.regions if r.shape_id == purple.shape_id)
    assert survivor.shape_id == purple.shape_id, "same stable id, no churn"
    assert survivor.area_mm2 > purple.area_mm2 * 1.5
    assert survivor.polygon.equals(Polygon(grown))
    _no_degenerate_stitches(plan2)
    # Every OTHER shape's id and geometry are untouched by one shape's edit.
    other_ids_before = {r.shape_id for r in result.regions} - {purple.shape_id}
    other_ids_after = {r.shape_id for r in result2.regions} - {purple.shape_id}
    assert other_ids_after == other_ids_before


# --- the cache seam ----------------------------------------------------------

def test_cache_key_sees_the_edit_fields():
    from digitizer_service.jobs import content_key

    img = b"pretend png"
    plain = {"target_width_mm": 80.0}
    with_ov = {**plain, "shape_overrides": {"S1": {"tier": "fill"}}}
    with_ov2 = {**plain, "shape_overrides": {"S1": {"tier": "run"}}}
    with_del = {**plain, "deleted_shape_ids": ["S1"]}

    assert content_key(img, plain) != content_key(img, with_ov)
    assert content_key(img, with_ov) != content_key(img, with_ov2)
    assert content_key(img, plain) != content_key(img, with_del)
    assert content_key(img, with_ov) == content_key(img, dict(with_ov))


def test_cache_key_sees_a_boundary_override():
    from digitizer_service.jobs import content_key

    img = b"pretend png"
    plain = {"target_width_mm": 80.0}
    a = {**plain, "shape_overrides": {"S1": {"boundary_override": [[0, 0], [1, 0], [1, 1]]}}}
    b = {**plain, "shape_overrides": {"S1": {"boundary_override": [[0, 0], [2, 0], [2, 2]]}}}

    assert content_key(img, plain) != content_key(img, a)
    assert content_key(img, a) != content_key(img, b)
    assert content_key(img, a) == content_key(img, dict(a))
