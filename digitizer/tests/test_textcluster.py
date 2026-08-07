"""`textcluster.detect_text_clusters` — geometry-only "is this a word" tagger.

Fixtures are synthetic rectangles standing in for rescued letter glyphs, at
the scale `test_run_tier.py`'s subline fixture established as realistic: a
1.9 mm-tall subline with letters spaced about 2.3 mm apart (`_subline_image`,
20 px steps at 8.75 px/mm). Every candidate here carries
`meta["rescued_small_shape"] = True` by hand — this module trusts that flag,
it does not re-derive it (Step 1 already owns that decision).

**Default rectangle width is deliberately thin (0.3mm at 1.8mm tall, not the
original 0.9mm)** — `textcluster.STROKE_CV_MAX`'s docstring measured that a
solid axis-aligned rectangle's per-pixel stroke-width CV is dominated by the
taper at its two ends (universal to any stroke's free tip, but a much larger
fraction of a plain rectangle's total skeleton length than a real letter's
more complex one), and a 0.9mm-wide rectangle at this height scores CV 0.458
— well above even the real benchmark fixture's non-letter fragments (max
0.461), i.e. indistinguishable from genuine noise under the new filter. Every
explicit width below (the varied-width regularization fixture, the
"clearly-different-scale" big row) is chosen the same way: thin enough to
clear `STROKE_CV_MAX` at this module's own real-measured threshold, not
picked to dodge the filter under test.
"""
from __future__ import annotations

import random

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.textcluster import (
    SHAPE_CONTEXT_MAX_DIST,
    _candidates,
    _stroke_stats_mm,
    detect_text_clusters,
    regularize_text_clusters,
)

# A throwaway Prep: nothing in the current algorithm reads it (regions already
# carry mm-space polygons), but the public signature matches
# `tag_enclosed_background`'s shape on purpose, so a placeholder is threaded
# through rather than the signature narrowed.
_P = Prep(rgb=None, bg_mask=None, px_per_mm=1.0, art_bbox=(0, 0, 1, 1))


def _rect(cx: float, cy: float, w: float, h: float) -> Polygon:
    return Polygon([(cx - w / 2, cy - h / 2), (cx + w / 2, cy - h / 2),
                     (cx + w / 2, cy + h / 2), (cx - w / 2, cy + h / 2)])


def _letter(shape_id: str, cx: float, cy: float, w: float = 0.3, h: float = 1.8,
            rescued: bool = True) -> Region:
    meta = {"rescued_small_shape": True} if rescued else {}
    poly = _rect(cx, cy, w, h)
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number="1", area_mm2=poly.area, meta=meta)


def _row(prefix: str, n: int, x0: float = 0.0, y: float = 0.0,
         spacing: float = 2.3, w: float = 0.3, h: float = 1.8) -> list[Region]:
    """A row of `n` similarly-sized/spaced rescued "letters" — the subline
    shape distilled to its geometry, one glyph per Region."""
    return [_letter(f"{prefix}{i}", x0 + i * spacing, y, w, h)
            for i in range(n)]


def _row_varied_width(prefix: str, widths: list[float], x0: float = 0.0,
                       y: float = 0.0, spacing: float = 2.3,
                       h: float = 1.8) -> list[Region]:
    """A row of rescued "letters" at one shared height/spacing but each its
    OWN width — a cluster whose members' individually-measured stroke widths
    genuinely differ, the fixture `regularize_text_clusters`'s variance-drop
    test needs. Widths stay within `SIMILARITY_RATIO` of each other so the
    row still clusters as one group (that's a precondition of the test, not
    the thing under test)."""
    return [_letter(f"{prefix}{i}", x0 + i * spacing, y, w, h)
            for i, w in enumerate(widths)]


def _stroke_mm_of(poly: Polygon) -> float | None:
    """Same measurement `_stroke_stats_mm` gives `detect_text_clusters`
    itself, applied directly to a bare polygon (before/after comparisons
    need to measure a polygon that may not be attached to a real Region)."""
    return _stroke_stats_mm(Region(shape_id="tmp", polygon=poly, thread_index=0,
                                    thread_number="1", area_mm2=poly.area))


def _degenerate_region(shape_id: str, cx: float, cy: float) -> Region:
    """A shell exactly cancelled by an identically-shaped hole: zero area,
    and `build_shape_field` rasterizes it to an empty mask -> `None`. This is
    the one reliable way to make a real `Polygon` degenerate enough to hit
    that guard (a merely tiny polygon still rasterizes to >=1 px, verified
    empirically before picking this fixture)."""
    ring = [(cx, cy), (cx + 1, cy), (cx + 1, cy + 1), (cx, cy + 1)]
    poly = Polygon(ring, [ring])
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number="1", area_mm2=0.0,
                  meta={"rescued_small_shape": True})


def test_row_of_letters_forms_one_tagged_cluster():
    regions = _row("L", 5)
    detect_text_clusters(regions, _P)

    cluster_ids = {r.meta.get("text_cluster_id") for r in regions}
    assert all(r.meta.get("text_candidate") is True for r in regions)
    assert len(cluster_ids) == 1 and None not in cluster_ids

    stroke_values = {r.meta.get("text_cluster_stroke_mm") for r in regions}
    assert len(stroke_values) == 1, \
        "every member must carry the CLUSTER's shared stroke value, not its own"


def test_single_isolated_shape_is_untagged():
    regions = [_letter("Lone", 0.0, 0.0)]
    detect_text_clusters(regions, _P)
    assert "text_candidate" not in regions[0].meta
    assert "text_cluster_id" not in regions[0].meta


def test_two_below_minimum_are_untagged():
    """Letters come in groups; two similarly-sized close shapes is not
    enough signal on its own (see `MIN_CLUSTER_MEMBERS`'s docstring)."""
    regions = _row("Pair", 2)
    detect_text_clusters(regions, _P)
    for r in regions:
        assert "text_candidate" not in r.meta


def test_two_separated_clusters_get_distinct_ids():
    near = _row("A", 4, x0=0.0)
    far = _row("B", 4, x0=500.0)  # far beyond any proximity multiple of height
    regions = near + far
    detect_text_clusters(regions, _P)

    assert all(r.meta.get("text_candidate") is True for r in regions)
    id_a = {r.meta["text_cluster_id"] for r in near}
    id_b = {r.meta["text_cluster_id"] for r in far}
    assert len(id_a) == 1 and len(id_b) == 1
    assert id_a != id_b, "distant groups must not merge into one cluster"


def test_clusters_of_clearly_different_scale_stay_separate():
    """Close in space but not in size: a row of ordinary letters right next
    to a row of much taller/thicker "letters" must not merge just because
    they are near each other — bbox-height/stroke similarity is its own
    gate, independent of proximity."""
    small = _row("S", 4, x0=0.0, y=0.0)
    # 4-5x the small letters (same aspect ratio, so it clears STROKE_CV_MAX
    # the same way the default width does — see the module docstring).
    big = _row("G", 4, x0=0.0, y=6.0, w=1.3, h=8.0)
    regions = small + big
    detect_text_clusters(regions, _P)

    assert all(r.meta.get("text_candidate") is True for r in regions)
    id_small = {r.meta["text_cluster_id"] for r in small}
    id_big = {r.meta["text_cluster_id"] for r in big}
    assert len(id_small) == 1 and len(id_big) == 1
    assert id_small != id_big


def test_non_rescued_neighbor_is_not_swept_into_the_cluster():
    """A region with no `rescued_small_shape` key was never a candidate —
    geometric closeness to a real cluster must not pull it in."""
    regions = _row("C", 4)
    bystander = Region(
        shape_id="Bystander", polygon=_rect(2.3 * 4, 0.0, 0.9, 1.8),
        thread_index=0, thread_number="1", area_mm2=0.9 * 1.8, meta={})
    regions.append(bystander)
    detect_text_clusters(regions, _P)

    assert bystander.meta == {}, "never a candidate -> meta untouched entirely"
    cluster = [r for r in regions if r.shape_id != "Bystander"]
    assert all(r.meta.get("text_candidate") is True for r in cluster)


def test_determinism_regardless_of_input_order():
    """Two INDEPENDENT builds of the same five letters (never the same Region
    objects — reusing objects across both calls would let the second call's
    result ride on the first's already-written meta rather than proving
    anything about order)."""
    regions = _row("D", 5)
    shuffled = _row("D", 5)
    random.Random(7).shuffle(shuffled)

    detect_text_clusters(regions, _P)
    detect_text_clusters(shuffled, _P)

    by_id = {r.shape_id: r.meta.get("text_cluster_id") for r in regions}
    by_id_shuffled = {r.shape_id: r.meta.get("text_cluster_id") for r in shuffled}
    assert by_id == by_id_shuffled
    assert None not in by_id.values()


def test_degenerate_polygon_is_skipped_not_crashed():
    """`build_shape_field` returning `None` for a degenerate candidate must
    not crash the pass, and must not block the OTHER candidates from being
    clustered normally."""
    regions = _row("E", 4)
    regions.append(_degenerate_region("Bad", cx=1.0, cy=0.0))

    detect_text_clusters(regions, _P)  # must not raise

    bad = next(r for r in regions if r.shape_id == "Bad")
    assert "text_candidate" not in bad.meta, \
        "a degenerate candidate must be excluded, not crash or join a cluster"

    good = [r for r in regions if r.shape_id != "Bad"]
    assert all(r.meta.get("text_candidate") is True for r in good)
    assert len({r.meta["text_cluster_id"] for r in good}) == 1


# --- regularize_text_clusters (Step 5) -------------------------------------


def test_regularize_reduces_stroke_width_variance_across_cluster():
    """The point of regularization: a cluster whose members have genuinely
    different individually-measured stroke widths ends up with LESS spread
    after every member is redrawn at the cluster's shared target width —
    measured from real geometry (each member's own new skeleton), not just
    "the function ran without raising"."""
    widths = [0.18, 0.21, 0.24, 0.27, 0.30]
    regions = _row_varied_width("V", widths)
    before_polys = [r.polygon for r in regions]

    detect_text_clusters(regions, _P)
    assert all(r.meta.get("text_cluster_id") for r in regions), \
        "fixture must actually form one cluster for this test to mean anything"

    before_stroke = [_stroke_mm_of(p) for p in before_polys]
    assert all(v is not None for v in before_stroke)

    regularize_text_clusters(regions, _P)

    assert not any(r.meta.get("text_cluster_regularize_skipped") for r in regions), \
        "this fixture is deliberately simple -- every member should regularize cleanly"

    after_stroke = [_stroke_mm_of(r.polygon) for r in regions]
    assert all(v is not None for v in after_stroke)

    before_var, after_var = np.var(before_stroke), np.var(after_stroke)
    assert after_var < before_var, (
        f"regularization must reduce stroke-width variance: "
        f"before={before_stroke} (var={before_var:.6g}), "
        f"after={after_stroke} (var={after_var:.6g})"
    )


def test_regularize_updates_area_mm2_to_match_new_polygon():
    """Same contract `boundary_override` already holds: `area_mm2` must never
    drift from `polygon.area` after a geometry replacement."""
    widths = [0.18, 0.21, 0.24, 0.27, 0.30]
    regions = _row_varied_width("A", widths)
    detect_text_clusters(regions, _P)
    regularize_text_clusters(regions, _P)

    regularized = [r for r in regions if not r.meta.get("text_cluster_regularize_skipped")]
    assert regularized, "fixture is expected to regularize cleanly"
    for r in regularized:
        assert r.area_mm2 == pytest.approx(r.polygon.area)


def test_regularize_skips_when_buffered_result_is_too_small_to_sew():
    """A cluster stroke width far too thin to clear the sewability floor once
    buffered must fail OPEN: no geometry change, a skip flag instead of a
    crash or a silently-unsewable shape."""
    r = _letter("Tiny", 0.0, 0.0, w=0.9, h=1.8)
    r.meta["text_cluster_id"] = "TCtest"
    r.meta["text_cluster_stroke_mm"] = 0.01  # buffers to well under the floor
    original_coords = list(r.polygon.exterior.coords)

    regularize_text_clusters([r], _P)  # must not raise

    assert r.meta.get("text_cluster_regularize_skipped") is True
    assert list(r.polygon.exterior.coords) == original_coords, \
        "a failed regularization must leave the polygon byte-identical"


def test_regularize_skips_a_degenerate_polygon_without_crashing():
    """`build_shape_field` returning `None` (the same degenerate fixture
    `detect_text_clusters`'s own guard test uses) must not crash this pass
    either, even for a region tagged directly rather than via detection."""
    r = _degenerate_region("BadReg", cx=1.0, cy=0.0)
    r.meta["text_cluster_id"] = "TCtest"
    r.meta["text_cluster_stroke_mm"] = 0.1
    original_coords = list(r.polygon.exterior.coords)

    regularize_text_clusters([r], _P)  # must not raise

    assert r.meta.get("text_cluster_regularize_skipped") is True
    assert list(r.polygon.exterior.coords) == original_coords


def test_regularize_leaves_non_text_regions_completely_untouched():
    """No `text_cluster_id` at all -> not a candidate for this pass, exactly
    like `detect_text_clusters`'s own untagged case: no new meta keys, the
    polygon untouched."""
    r = _letter("Plain", 0.0, 0.0, rescued=False)
    original_coords = list(r.polygon.exterior.coords)
    original_meta = dict(r.meta)

    regularize_text_clusters([r], _P)

    assert r.meta == original_meta
    assert list(r.polygon.exterior.coords) == original_coords


# --- new candidate filters: stroke-width CV, aspect ratio, bbox nesting ----
#
# All three tested directly against `_candidates` (not the full
# `detect_text_clusters` clustering pass) so each test isolates the ONE
# filter under test -- going through proximity/similarity clustering as
# well would leave an ambiguity about which gate actually produced a given
# exclusion. Real-fixture calibration for every threshold below lives in
# `textcluster.py`'s own "Candidate filters" docstring section.


def _dumbbell(shape_id: str, cx: float = 0.0, cy: float = 0.0) -> Region:
    """A thin bar merged with a much wider block at one end: the same
    overall bbox height/aspect a normal letter could have, but a stroke
    width that varies far more along its own skeleton than any real letter
    does -- the part-letter/part-blob case `STROKE_CV_MAX` exists to
    reject. Real measurement: CV 0.422, comfortably over the 0.32 threshold,
    while its aspect ratio (0.667) sits comfortably inside bounds -- this
    shape is excluded by the CV filter specifically, not aspect."""
    poly = Polygon([
        (cx - 0.15, cy - 0.9), (cx + 0.15, cy - 0.9), (cx + 0.15, cy + 0.3),
        (cx + 0.6, cy + 0.3), (cx + 0.6, cy + 0.9), (cx - 0.6, cy + 0.9),
        (cx - 0.6, cy + 0.3), (cx - 0.15, cy + 0.3),
    ])
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number="1", area_mm2=poly.area,
                  meta={"rescued_small_shape": True})


def _wide_fragment(shape_id: str, cx: float = 0.0, cy: float = 0.0) -> Region:
    """A landscape (wide/short) shape -- aspect 6.67, well outside
    `ASPECT_RATIO_MAX` -- the same orientation the real benchmark fixture's
    own 3 non-letter fragments measure (1.778-2.125, see the module
    docstring). Real measurement: CV 0.262, comfortably under
    `STROKE_CV_MAX`, so this shape is excluded by the aspect filter
    specifically, not CV."""
    return _letter(shape_id, cx, cy, w=2.0, h=0.3)


def test_high_stroke_cv_fragment_is_excluded_from_candidacy():
    letters = _row("N", 4)
    fragment = _dumbbell("Frag")
    cands = _candidates(letters + [fragment])
    ids = {c.region.shape_id for c in cands}
    assert "Frag" not in ids
    assert ids == {r.shape_id for r in letters}, \
        "the CV filter must exclude only the high-variance fragment, not the real letters"


def test_extreme_aspect_ratio_fragment_is_excluded_from_candidacy():
    letters = _row("N", 4)
    fragment = _wide_fragment("Wide")
    cands = _candidates(letters + [fragment])
    ids = {c.region.shape_id for c in cands}
    assert "Wide" not in ids
    assert ids == {r.shape_id for r in letters}, \
        "the aspect filter must exclude only the landscape fragment, not the real letters"


def test_nested_bbox_fragment_is_excluded_from_candidacy():
    """A small candidate whose bbox sits fully inside a larger candidate's
    bbox is dropped even though it independently clears CV and aspect on
    its own (real letters in a row are never nested inside a sibling's
    footprint -- see the module docstring's real-fixture evidence)."""
    outer = _letter("Outer", 0.0, 0.0)                    # default 0.3x1.8mm
    inner = _letter("Inner", 0.0, 0.0, w=0.1, h=0.6)       # nested concentric, smaller
    others = _row("N", 3, x0=5.0)

    cands = _candidates([outer, inner] + others)
    ids = {c.region.shape_id for c in cands}
    assert "Inner" not in ids
    assert "Outer" in ids
    assert ids == {r.shape_id for r in others} | {"Outer"}


def test_nesting_does_not_exclude_equal_sized_bboxes():
    """Two candidates with the exact same bbox (neither strictly larger)
    must not exclude each other -- there is no basis to prefer one, and
    dropping both would silently lose real candidates over a tie."""
    a = _letter("A", 0.0, 0.0)
    b = _letter("B", 0.0, 0.0)  # identical position/size -> identical bbox
    others = _row("N", 3, x0=5.0)

    cands = _candidates([a, b] + others)
    ids = {c.region.shape_id for c in cands}
    assert {"A", "B"} <= ids


# --- Shape Context gate (Step 5 addition): before/after glyph-plausibility -


def _l_shape(long_arm: float = 1.8, short_arm: float = 0.5, thick: float = 0.35) -> Polygon:
    return Polygon([
        (0, 0), (thick, 0), (thick, long_arm - thick),
        (short_arm, long_arm - thick), (short_arm, long_arm),
        (0, long_arm),
    ])


def test_regularize_gates_on_shape_context_distance():
    """A cluster member whose target stroke half-width is grossly
    mismatched from its own true stroke (still within what
    `SIMILARITY_RATIO`'s 0.5 floor already permits two clustered members to
    differ by) buffers into something perfectly VALID and sewable -- the
    pre-existing `_skeleton_buffer_polygon` guard would not have caught it
    -- but structurally very different from its own original shape. The
    Shape Context gate (`SHAPE_CONTEXT_MAX_DIST`) is what catches that one:
    same skip discipline as every other guard in this function, plus a
    dedicated `text_cluster_regularize_shape_changed` flag and the measured
    distance recorded either way. A correctly-matched radius on the same
    base shape regularizes cleanly, for direct comparison."""
    poly_matched = _l_shape()
    poly_mismatched = _l_shape()
    matched = Region(shape_id="Matched", polygon=poly_matched, thread_index=0,
                      thread_number="1", area_mm2=poly_matched.area,
                      meta={"text_cluster_id": "TCtest", "text_cluster_stroke_mm": 0.175})
    mismatched = Region(shape_id="Mismatched", polygon=poly_mismatched, thread_index=0,
                         thread_number="1", area_mm2=poly_mismatched.area,
                         meta={"text_cluster_id": "TCtest", "text_cluster_stroke_mm": 0.9})
    matched_before_coords = list(matched.polygon.exterior.coords)
    mismatched_before_coords = list(mismatched.polygon.exterior.coords)

    regularize_text_clusters([matched, mismatched], _P)

    # Matched: regularizes cleanly, a low distance recorded, within the gate.
    assert not matched.meta.get("text_cluster_regularize_skipped")
    assert "text_cluster_regularize_shape_changed" not in matched.meta
    assert list(matched.polygon.exterior.coords) != matched_before_coords, \
        "a clean regularization must actually replace the geometry"
    assert isinstance(matched.meta.get("text_cluster_shape_context_dist"), float)
    assert matched.meta["text_cluster_shape_context_dist"] <= SHAPE_CONTEXT_MAX_DIST

    # Mismatched: buffers into a valid/sewable polygon (the old guard alone
    # would have accepted it) but the shape-context gate must skip it.
    assert mismatched.meta.get("text_cluster_regularize_skipped") is True
    assert mismatched.meta.get("text_cluster_regularize_shape_changed") is True
    assert isinstance(mismatched.meta.get("text_cluster_shape_context_dist"), float)
    assert mismatched.meta["text_cluster_shape_context_dist"] > SHAPE_CONTEXT_MAX_DIST
    assert list(mismatched.polygon.exterior.coords) == mismatched_before_coords, \
        "a shape-context-gated skip must leave the polygon byte-identical, same discipline as every other skip"
