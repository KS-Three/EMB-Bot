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
from digitizer_core.regions import Region, match_shape_ids
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

    c = cfg(
        deleted_shape_ids=[tiny.shape_id, "SNOPE"],
        shape_overrides={
            purple.shape_id: {"thread_index": red.thread_index},  # recolor
            green.shape_id: {"tier": "fill"},                     # tier flip
            red.shape_id: {"fill_angle_deg": 90.0},               # angle
            blue.shape_id: {"layer": 99},                         # sew last
            "SNOPE2": {"tier": "satin"},                          # stale
        },
    )
    result2, plan2 = digitize(ART, c)
    return {
        "result": result2, "plan": plan2,
        "red": red, "blue": blue, "green": green, "purple": purple,
        "tiny": tiny,
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
    assert w["count"] == 2 and w["ids"] == ["SNOPE", "SNOPE2"]


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


# --- carry-forward -----------------------------------------------------------

def test_review_intent_rides_the_id_carry_forward():
    """`match_shape_ids` carries the operator's per-shape decisions onto the
    next generation, exactly as the config docstring promises for border and
    appliqué — and now for tier and fill angle too."""
    prev = [region(bar(10, 4), "OLD",
                   {"tier": "satin", "fill_angle_deg": 45.0, "border": "bean",
                    "applique": True, "layer": 3})]
    cur = [region(bar(10.2, 4.1), "NEW")]
    match_shape_ids(prev, cur)
    assert cur[0].shape_id == "OLD"
    assert cur[0].meta.get("tier") == "satin"
    assert cur[0].meta.get("fill_angle_deg") == 45.0
    assert cur[0].meta.get("border") == "bean"
    assert cur[0].meta.get("applique") is True
    assert cur[0].meta["layer"] == 0, "pipeline facts stay the new generation's"


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
