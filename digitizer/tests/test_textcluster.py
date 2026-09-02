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

import math
import random
import statistics
from unittest.mock import patch

import numpy as np
import pytest
from shapely.affinity import rotate as shapely_rotate
from shapely.geometry import Point, Polygon

from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.stage6_satin import satin_shape
from digitizer_core.textcluster import (
    SHAPE_CONTEXT_MAX_DIST,
    SATIN_ANGLE_RAYLEIGH_ALPHA,
    SATIN_HOUSE_BISECTOR_DEG,
    SATIN_HOUSE_FOURFOLD_MIN_R,
    _cluster_house_angle_deg,
    _bisector_deg,
    _fourfold_votes,
    _lettering_groups,
    _candidates,
    _stroke_stats_mm,
    detect_text_clusters,
    regularize_text_clusters,
    set_lettering_house_angle,
)

# Fixtures in this file are bare rectangles standing in for letters (see
# module docstring) -- geometrically fine for the SKELETON-BUFFER layer this
# file mostly tests, but they carry no real letterform content, so the
# OCR-confidence gate (`textcluster.py`'s "OCR-confidence quality gate"
# section; `tests/test_ocr_gate.py` covers IT in isolation, on real
# font-rendered glyphs) reads them as noise -- Tesseract has no reliable
# opinion about a plain rectangle, before OR after. Two tests below are
# testing the buffer/variance-reduction behavior specifically and patch the
# OCR gate to a permissive no-op for that reason, the same isolation
# `tests/test_pipeline.py` already uses to test one pass at a time.
_OCR_GATE_PATH = "digitizer_core.textcluster._ocr_regularization_hurts_legibility"

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
    after regularization — measured from real geometry (each member's own
    new skeleton), not just "the function ran without raising".

    Updated 2026-08-06 alongside the selective-regularization fix (see
    `textcluster.py`'s "Selective regularization" docstring section). The
    member widths here are BBOX widths, not stroke half-widths — a free-
    standing rectangle's own measured `_stroke_stats_mm` is a nonlinear,
    slightly asymmetric function of that (skeleton taper at the two free
    caps), measured directly for this exact fixture: own-stroke deviation
    from the cluster median comes out -18.3% (w=0.7), -11.7% (w=0.8), 0%
    (w=0.9, the median itself), +5.6% (w=1.0), +10.5% (w=1.1). Only the
    first clears `_REGULARIZE_SKIP_TOLERANCE` (15%) and regularizes; the
    other four are already close enough that replacing their polygons would
    buy no consistency at a real fidelity cost, so they now correctly skip.
    The variance-reduction this test exists to prove still holds — removing
    just the one real outlier is enough."""
    widths = [0.7, 0.8, 0.9, 1.0, 1.1]
    regions = _row_varied_width("V", widths)
    before_polys = [r.polygon for r in regions]

    before_stroke = [_stroke_mm_of(p) for p in before_polys]
    assert all(v is not None for v in before_stroke)

    # Tag the cluster directly rather than going through detect_text_clusters:
    # this test is about regularize_text_clusters's own behavior given an
    # already-formed cluster, not about _candidates's separate stroke-CV/
    # aspect-ratio/nesting filters -- these solid, wide rectangles (built to
    # hit exact, documented stroke-width percentages) are exactly the shape
    # class those filters correctly reject for DETECTION (see the module's
    # "Candidate filters" docstring), an unrelated concern this test isolates
    # from, the same way it already isolates from the OCR-confidence gate
    # below.
    cluster_stroke_mm = float(np.median(before_stroke))
    for r in regions:
        r.meta["text_cluster_id"] = "TCtest"
        r.meta["text_cluster_stroke_mm"] = cluster_stroke_mm

    # Isolate the skeleton-buffer/variance layer from the OCR-confidence
    # gate: these bare rectangles carry no real letterform content for
    # Tesseract to read, before or after (see module comment above).
    with patch(_OCR_GATE_PATH, return_value=False):
        regularize_text_clusters(regions, _P)

    # `text_cluster_regularize_skipped` is absent (not `False`) on a member
    # that DID regularize — same "absent means false" convention every
    # tagger in this module uses (see `detect_text_clusters`'s docstring).
    skipped = [r.meta.get("text_cluster_regularize_skipped") for r in regions]
    assert skipped == [None, True, True, True, True], (
        "only the one genuine outlier (w=0.7, -18.3% from the cluster "
        f"median) should regularize; got skipped={skipped}"
    )

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
    # Isolate from the OCR-confidence gate -- see the comment on the
    # variance-reduction test above; same bare-rectangle fixture, same
    # reason.
    with patch(_OCR_GATE_PATH, return_value=False):
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


# --- Selective regularization (2026-08-06 fix) ------------------------------
#
# Regression coverage for the real defect Kent reported on
# `testdata/photo/enthusiast_logo.png`: unconditional regularization
# replaced every tagged member's polygon, including members whose own
# geometry was already fine, which measurably damaged letterform fidelity
# (lost corners/holes, distorted proportions) for no consistency gain. See
# `textcluster.py`'s "Selective regularization" module-docstring section for
# the full evidence trail.


def _holed_letter(shape_id: str, cx: float, cy: float, w: float = 0.9,
                   h: float = 1.8, hole_w: float = 0.3,
                   hole_h: float = 0.9) -> Region:
    """A rescued "letter" with a real interior ring — an R/P-style counter,
    the shape class a skeleton-LINE buffer cannot faithfully reproduce (see
    the module docstring)."""
    outer = _rect(cx, cy, w, h)
    inner = _rect(cx, cy, hole_w, hole_h)
    poly = Polygon(outer.exterior.coords, [inner.exterior.coords])
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number="1", area_mm2=poly.area,
                  meta={"rescued_small_shape": True})


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


def test_regularize_skips_a_member_already_close_to_the_cluster_target():
    """A member within `_REGULARIZE_SKIP_TOLERANCE` of the cluster's target
    half-width is left completely untouched — the real-fixture case (13 of
    the benchmark subline's 14 members measured within +-11%, see the module
    docstring), reproduced as a minimal synthetic cluster: four letters at
    an identical width (the exact median, zero deviation) plus one genuine
    outlier far enough off to still need correction."""
    regions = _row_varied_width("W", [0.9, 0.9, 0.9, 0.9, 1.6])

    # Tag the cluster directly rather than going through detect_text_clusters
    # -- see the sibling variance test above for why: this is a
    # regularize_text_clusters-only test, isolated from _candidates's
    # separate stroke-CV/aspect-ratio/nesting detection filters.
    cluster_stroke_mm = float(np.median([_stroke_stats_mm(r) for r in regions]))
    for r in regions:
        r.meta["text_cluster_id"] = "TCtest"
        r.meta["text_cluster_stroke_mm"] = cluster_stroke_mm

    # Isolate the tolerance-skip layer from the (separately tested) Shape
    # Context gate too: the outlier's own 1.6mm width buffered all the way
    # to the 0.9mm cluster target is a genuinely large redraw, exactly the
    # kind of change SHAPE_CONTEXT_MAX_DIST exists to catch on its own --
    # not what THIS test isolates (see test_regularize_gates_on_shape_
    # context_distance for that gate's own dedicated test).
    with patch("digitizer_core.textcluster.SHAPE_CONTEXT_MAX_DIST", 999.0):
        regularize_text_clusters(regions, _P)

    at_median = regions[:4]
    outlier = regions[4]
    for r in at_median:
        assert r.meta.get("text_cluster_regularize_skipped") is True
        assert r.meta.get("text_cluster_regularize_skip_reason") == "already_consistent"
    assert not outlier.meta.get("text_cluster_regularize_skipped"), \
        "the genuine outlier must still regularize"


def test_regularize_never_replaces_a_member_with_a_real_interior_hole():
    """Unconditional, regardless of how far the member's own width is from
    the cluster target: a skeleton-line buffer cannot safely reproduce a
    real hole, so a holed member's polygon is never replaced — this is what
    kept the "A" in ENTHUSIAST's triangular counter from disappearing on the
    real fixture (that specific regression is covered end-to-end in
    `tests/test_stages.py`; this is the module-level unit case).

    Both `holed` and `plain_outlier` are measured (not assumed) to deviate
    from the cluster's target by well over `_REGULARIZE_SKIP_TOLERANCE`
    (-33.6% and +42.4% respectively) — wide enough that the tolerance check
    alone would send both to the buffer. The contrast is the point: only
    the member WITHOUT a hole actually gets replaced.
    """
    holed = _holed_letter("Hole", 0.0, 0.0, w=1.6, hole_w=0.5, hole_h=1.1)
    plain_outlier = _letter("Plain", 2.3, 0.0, w=1.6)
    regions = _row("P", 3, x0=4.6) + [holed, plain_outlier]

    # Tag the cluster directly rather than going through detect_text_clusters
    # -- see the variance test above for why: this is a regularize_text_
    # clusters-only test, isolated from _candidates's separate stroke-CV/
    # aspect-ratio/nesting detection filters (the wide, solid `plain_outlier`
    # rectangle built to prove a comparably-off member WITHOUT a hole still
    # regularizes is exactly the shape class those filters correctly reject
    # for DETECTION, an unrelated concern).
    cluster_stroke_mm = float(np.median([_stroke_stats_mm(r) for r in regions]))
    for r in regions:
        r.meta["text_cluster_id"] = "TCtest"
        r.meta["text_cluster_stroke_mm"] = cluster_stroke_mm

    original_coords = (list(holed.polygon.exterior.coords),
                        [list(r.coords) for r in holed.polygon.interiors])

    # Isolate from the (separately tested) Shape Context gate too: buffering
    # plain_outlier's 1.6mm width all the way to the cluster's much narrower
    # target is a genuinely large redraw on its own terms -- not what THIS
    # test isolates (see test_regularize_gates_on_shape_context_distance).
    with patch("digitizer_core.textcluster.SHAPE_CONTEXT_MAX_DIST", 999.0):
        regularize_text_clusters(regions, _P)

    assert holed.meta.get("text_cluster_regularize_skipped") is True
    assert holed.meta.get("text_cluster_regularize_skip_reason") == "has_interior_hole"
    assert list(holed.polygon.exterior.coords) == original_coords[0]
    assert len(holed.polygon.interiors) == 1
    assert [list(r.coords) for r in holed.polygon.interiors] == original_coords[1]

    assert not plain_outlier.meta.get("text_cluster_regularize_skipped"), \
        "a comparably-off member WITHOUT a hole must still regularize -- " \
        "proves the holed member above was protected by the hole, not " \
        "coincidentally by the tolerance check"


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

    # Isolate the Shape Context gate from the two OTHER, separately tested
    # gates in this same function: the tolerance-skip layer (`matched`'s own
    # true stroke is, by construction, close to its 0.175mm target -- exactly
    # what "already_consistent" correctly skips on its own terms, see
    # test_regularize_skips_a_member_already_close_to_the_cluster_target) and
    # the OCR-confidence gate (this fixture is a real polygon, not a blank
    # rectangle, so Tesseract genuinely reads something on it). This test
    # isolates what happens once a member actually reaches the buffer and
    # clears both those checks.
    with patch("digitizer_core.textcluster._REGULARIZE_SKIP_TOLERANCE", 0.0), \
         patch(_OCR_GATE_PATH, return_value=False):
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


# --- The house cross angle (Step 6) -------------------------------------------
#
# `_row`'s default glyph is a 0.3 x 1.8 mm bar: a VERTICAL stem, which is what
# block capitals are mostly made of. A cross has to span its stroke, so the
# right answer on vertical stems is a HORIZONTAL cross -- 0 deg on the
# [0, 180) axis these angles live on. That is the whole fixture: the letters
# run one way, the crosses come back the other.


def _circ_delta_deg(a: float, b: float) -> float:
    """Signed a->b difference on the half-circle these angles live on, folded
    to (-90, 90]. Comparing 179 deg against 1 deg as a 178 deg gap would be
    wrong twice over: they are 2 deg apart, and on an axis they are the same
    line."""
    return (b - a + 90.0) % 180.0 - 90.0


def _rotated(regions: list[Region], deg: float, origin) -> list[Region]:
    """The same cluster, rigidly rotated. Rotation changes no stroke width, no
    spacing ratio and no relative position, so a row that clustered before
    still clusters after -- the only thing under test is the angle."""
    out = []
    for r in regions:
        poly = shapely_rotate(r.polygon, deg, origin=origin)
        out.append(Region(shape_id=r.shape_id, polygon=poly, thread_index=0,
                          thread_number="1", area_mm2=poly.area,
                          meta={"rescued_small_shape": True}))
    return out


def _angles_of(regions: list[Region]) -> list[float]:
    return [r.meta["satin_angle_deg"] for r in regions
            if "satin_angle_deg" in r.meta]


def test_a_row_of_vertical_stems_gets_a_horizontal_house_angle():
    regions = _row("L", 5)
    detect_text_clusters(regions, _P)
    set_lettering_house_angle(regions, _P)

    angles = _angles_of(regions)
    assert len(angles) == len(regions), "every member of the word should be angled"
    # Horizontal crosses over vertical stems. Loose tolerance on purpose: the
    # votes come off a raster skeleton, so a couple of degrees of quantisation
    # is expected and harmless -- what must not happen is 90 deg out.
    assert abs(_circ_delta_deg(0.0, angles[0])) < 5.0, angles[0]


def test_every_letter_in_a_word_gets_the_SAME_angle():
    """The point of the feature. Kent's complaint was not that any one letter
    was wrong, it was that they disagreed with each other."""
    regions = _row("L", 5)
    detect_text_clusters(regions, _P)
    set_lettering_house_angle(regions, _P)

    assert len(set(_angles_of(regions))) == 1


def test_the_house_angle_TRACKS_a_rotated_wordmark():
    """A hardcoded angle would pass the two tests above and fail this one. A
    logotype set on a slant has to get its own angle read off the artwork, not
    the horizontal one that happens to suit an upright fixture.

    Both rows are tagged BY HAND rather than through `detect_text_clusters`,
    because that pass does not tag a rotated row at all (measured here,
    2026-08-27: its candidate/link tests read axis-aligned bounding boxes, so
    a 30 deg row fails them). That is a limitation of DETECTION and is out of
    scope for this pass, which is only asked what angle a cluster should sew
    at once something has decided it is one. Tagging both rows the same way
    also leaves rotation as the single variable between them."""
    upright = _row("L", 5)
    turned = _rotated(_row("L", 5), 30.0, origin=(4.6, 0.0))
    for row, cid in ((upright, "upright"), (turned, "turned")):
        for r in row:
            r.meta["text_cluster_id"] = cid
        set_lettering_house_angle(row, _P)

    assert _angles_of(upright) and _angles_of(turned)
    shift = _circ_delta_deg(_angles_of(upright)[0], _angles_of(turned)[0])
    assert abs(shift - 30.0) < 5.0, f"expected ~30 deg of shift, got {shift}"


def test_an_angle_already_set_on_a_shape_is_not_overwritten():
    """Per-shape intent beats a derived default, the precedence
    `config.satin_angle_deg`'s own comment describes."""
    regions = _row("L", 5)
    detect_text_clusters(regions, _P)
    regions[2].meta["satin_angle_deg"] = 77.0
    set_lettering_house_angle(regions, _P)

    assert regions[2].meta["satin_angle_deg"] == 77.0
    others = {r.meta["satin_angle_deg"] for r in regions if r is not regions[2]}
    assert len(others) == 1 and 77.0 not in others


def test_shapes_that_are_not_a_text_cluster_get_no_angle_at_all():
    """Absent means "per-stroke tangent, exactly as before" -- the guarantee
    that every golden in the suite still holds."""
    regions = _row("L", 2)          # below MIN_CLUSTER_MEMBERS
    detect_text_clusters(regions, _P)
    set_lettering_house_angle(regions, _P)

    assert not any("satin_angle_deg" in r.meta for r in regions)


def test_a_cluster_whose_strokes_disagree_is_left_alone():
    """No dominant direction means there is no house angle to find. Forcing
    one would be worse than the per-stroke tangent it replaces, so the pass
    writes nothing."""
    members = _row("L", 4)
    for r in members:
        r.meta["text_cluster_id"] = "mixed"
    # Four bars 45 deg apart: in doubled-angle space their votes sit at 0, 90,
    # 180 and 270 deg and cancel exactly, so the resultant is ~0 by
    # construction rather than by a tuned fixture.
    spread = []
    for i, r in enumerate(members):
        poly = shapely_rotate(r.polygon, i * 45.0, origin="centroid")
        spread.append(Region(shape_id=r.shape_id, polygon=poly, thread_index=0,
                             thread_number="1", area_mm2=poly.area,
                             meta={"text_cluster_id": "mixed"}))
    set_lettering_house_angle(spread, _P)

    assert not any("satin_angle_deg" in r.meta for r in spread)


def test_a_long_stem_outweighs_short_arms_running_across_it():
    """Votes are weighted by LENGTH, not counted per skeleton sample, and this
    is the fixture where that decides the outcome.

    `build_shape_field` normalises raster SIZE rather than resolution, so every
    member comes back with roughly the same pixel count whatever its physical
    size — a 24 mm stem and a 1.6 mm arm each contribute about as many skeleton
    samples. Counting samples therefore lets two short arms dilute a stem that
    carries an order of magnitude more thread: measured here, chance-corrected
    n_eff*R^2 falls to 4.8 against a 6.9 critical value and the group gets NO
    angle at all. Weighted by mm it reaches 13.2 and the stem decides, which is
    the mechanism
    `stage6_satin`'s own note attributes the pro's near-horizontal crosses to —
    "vertical strokes carrying most of the area".
    """
    stem = _rect(0.0, 0.0, 1.6, 24.0)
    arms = [_rect(8.0 + i * 3.0, 0.0, 1.6, 0.4) for i in range(2)]
    members = [
        Region(shape_id=f"S{i}", polygon=poly, thread_index=0,
               thread_number="1", area_mm2=poly.area)
        for i, poly in enumerate([stem, *arms])
    ]
    # Straight at the derivation, not through the pass: a stem and two stubby
    # arms are not a line of lettering and `_lettering_groups` is right to
    # refuse them. What is under test here is how the votes are WEIGHTED once
    # something has decided a set of shapes belongs together.
    angles = [a for a in [_cluster_house_angle_deg(members)] if a is not None]
    assert angles, "the stem should carry the group to a confident angle"
    # Horizontal crosses over the vertical stem, not vertical ones over the arms.
    assert abs(_circ_delta_deg(0.0, angles[0])) < 5.0, angles[0]


def _median_cross_angle(runs) -> float:
    """Median direction of the actual cross stitches, mod 180. Sub-0.05 mm
    steps are skipped: they are travel/tie artifacts, not crosses, and their
    direction is numerically meaningless at that length."""
    angles = []
    for run in runs:
        for (x0, y0), (x1, y1) in zip(run.points, run.points[1:]):
            dx, dy = x1 - x0, y1 - y0
            if math.hypot(dx, dy) > 0.05:
                angles.append(math.degrees(math.atan2(dy, dx)) % 180.0)
    return statistics.median(angles)


def test_the_derived_angle_actually_MOVES_THE_STITCHES():
    """The one test that would fail if this pass were inert.

    Everything above checks the number written into `Region.meta`. This
    follows that number into `satin_shape` and measures the crosses that come
    out, because a house angle nothing consumes is worth nothing — and the
    whole reason this pass exists is that the machinery to consume it was
    built on 2026-08-26 and then never fed.

    Measured here on a vertical stem: today's per-stroke tangent yields a
    median cross of ~160.6 deg — 19.4 deg off the perpendicular it is
    nominally aiming at, the raster wander `_rail_points` smooths but cannot
    remove. The house angle brings it to 0.0.
    """
    stem = _rect(0.0, 0.0, 1.2, 12.0)
    members = [
        Region(shape_id=f"S{i}", polygon=poly, thread_index=0,
               thread_number="1", area_mm2=poly.area,
               meta={"text_cluster_id": "word"})
        for i, poly in enumerate([stem, _rect(4.0, 0.0, 1.2, 12.0),
                                  _rect(8.0, 0.0, 1.2, 12.0)])
    ]
    set_lettering_house_angle(members, _P)
    house = members[0].meta["satin_angle_deg"]

    without, _ = satin_shape(stem, "S0", underlay_style="none",
                             trim_at_mm=3.0, angle_deg=None)
    with_, _ = satin_shape(stem, "S0", underlay_style="none",
                           trim_at_mm=3.0, angle_deg=house)

    off_without = abs(_circ_delta_deg(house, _median_cross_angle(without)))
    off_with = abs(_circ_delta_deg(house, _median_cross_angle(with_)))
    # Two independent claims, both with real margin against the 19.4 deg
    # measured above: the crosses were genuinely off the house angle before,
    # and they land on it after.
    assert off_without > 5.0, f"nothing to fix: crosses already at {off_without:.1f} deg"
    assert off_with < 5.0, f"house angle not honoured: {off_with:.1f} deg off"


# --- Finding the lettering in the first place (Step 6b) -----------------------


def test_letters_are_found_without_the_rescued_small_shape_flag():
    """The bug this pass shipped with. It originally grouped by
    `detect_text_clusters`' `text_cluster_id`, whose candidate set is gated on
    `rescued_small_shape` — a flag ordinary lettering never carries. Measured
    on Kent's Becker Marine logo: 0 of 17 regions had it, so the feature was
    inert on the exact artwork the complaint came from."""
    regions = _row("L", 5, w=1.2, h=12.0)
    for r in regions:
        r.meta.pop("rescued_small_shape", None)
    assert not any(r.meta for r in regions), "fixture must carry no flags at all"

    set_lettering_house_angle(regions, _P)
    assert len(_angles_of(regions)) == len(regions)


def test_two_lines_of_different_size_do_not_merge_into_one_group():
    """A logotype's second line must get its own angle, not be averaged into
    the first. On the Becker logo the module's own `SIMILARITY_RATIO` (0.5)
    merged 13 mm capitals with an arched 18-27 mm line into one 11-member
    group whose strokes then cancelled to no angle at all."""
    # 13 and 20 mm: a ratio of 0.65, deliberately BETWEEN the module's own
    # SIMILARITY_RATIO (0.5, which merges them) and SATIN_ANGLE_HEIGHT_RATIO
    # (0.8, which does not). Heights further apart would separate under either
    # and the test would prove nothing.
    small = _row("S", 4, y=0.0, w=1.2, h=13.0, spacing=3.5)
    big = _row("B", 4, y=40.0, w=1.6, h=20.0, spacing=5.0)
    groups = _lettering_groups(small + big)

    assert len(groups) == 2, [len(g) for g in groups]
    assert {len(g) for g in groups} == {4}


def test_an_isotropic_group_is_rejected_however_many_members_it_has():
    """The gate is a significance test, so the obvious way to break it is to
    pile on members until noise looks significant. Circular annuli have no
    stroke direction at all; measured, they sit at R = 0.008 and nR^2 stays
    far under the critical value even at 24 of them, because R falls toward
    zero under a true null instead of holding at a floor."""
    annuli = []
    for i in range(24):
        c = Point(i * 16.0, 0.0)
        poly = c.buffer(6.0).difference(c.buffer(5.4))
        annuli.append(Region(shape_id=f"A{i}", polygon=poly, thread_index=0,
                             thread_number="1", area_mm2=poly.area))
    assert _cluster_house_angle_deg(annuli) is None


def test_a_weak_but_real_direction_over_many_strokes_is_ADMITTED():
    """The case the borrowed 0.25 coherence floor got wrong, and the reason
    the gate is chance-corrected.

    Eight bars fanned across 140 deg sit at R = 0.209 — under 0.25, so a raw
    floor rejects them — but over n_eff = 399 weighted votes that is nR^2 =
    17.5 against a 6.9 critical value. R = 0.209 is not an arbitrary target:
    it is the band Kent's own lettering measures in (MARINE 0.197, BECKER
    0.203), which the raw floor rejected and left the whole feature inert.
    """
    bars = []
    for i in range(8):
        poly = shapely_rotate(_rect(i * 4.0, 0.0, 1.0, 8.0), i * 140.0 / 8,
                              origin="centroid")
        bars.append(Region(shape_id=f"F{i}", polygon=poly, thread_index=0,
                           thread_number="1", area_mm2=poly.area))
    assert _cluster_house_angle_deg(bars) is not None


def test_the_same_weak_direction_over_FEW_strokes_is_rejected():
    """The other half of the same claim: the gate must read sample size, not
    just the resultant. Three annuli carry the same nothing that 24 do, over
    far fewer votes, and neither reading may clear on them.

    This fixture was three buffered SQUARE rings until the four-fold reading
    landed (2026-09-02). A square ring is not directionless -- its sides are
    two orthogonal families, which is exactly the structure the second
    reading exists to find -- and under this pipeline a 10 mm ring's skeleton
    survives spur pruning only as a few millimetres of remnant per corner
    (measured: 2.5-3.5 mm of chain per ring after `_trim_ends`, the corner
    arcs), so whatever it reads is a handful of votes at 45 deg either way.
    Not a fixture for any claim about direction."""
    annuli = []
    for i in range(3):
        c = Point(i * 16.0, 0.0)
        poly = c.buffer(6.0).difference(c.buffer(5.4))
        annuli.append(Region(shape_id=f"A{i}", polygon=poly, thread_index=0,
                             thread_number="1", area_mm2=poly.area))
    assert _cluster_house_angle_deg(annuli) is None


def test_the_four_fold_grain_stays_well_under_the_floor():
    """The four-fold reading's null is BIASED: a rasterised circle's skeleton
    keeps a small four-fold grain even after resampling at
    `SATIN_HOUSE_CHORD_PX`, and with enough annuli that grain becomes
    "significant" (24 of them clear the Rayleigh bar). The effect-size floor
    is what rejects it, so the margin between the grain and the floor is the
    thing to pin: if a raster-resolution change ever pushes the grain up
    toward the floor, this is the test that says so. Measured 0.051 at 4 px
    against a 0.25 floor; asserted at a third of the floor."""
    annuli = []
    for i in range(24):
        c = Point(i * 16.0, 0.0)
        poly = c.buffer(6.0).difference(c.buffer(5.4))
        annuli.append(Region(shape_id=f"A{i}", polygon=poly, thread_index=0,
                             thread_number="1", area_mm2=poly.area))
    votes = _fourfold_votes(annuli)
    assert votes is not None
    resultant, n_eff, _axis = votes
    assert resultant < SATIN_HOUSE_FOURFOLD_MIN_R / 3.0, resultant
    # And the reason the floor exists at all: over this many votes the
    # residual IS significant, so significance alone would admit it.
    assert n_eff * resultant * resultant > -math.log(SATIN_ANGLE_RAYLEIGH_ALPHA)
    assert _cluster_house_angle_deg(annuli) is None


def test_raw_pixel_steps_would_have_seen_a_four_fold_grain():
    """Why the four-fold votes are resampled and the doubled votes are not.
    Four bars 45 deg apart cancel in BOTH angle spaces by construction, yet
    on raw 8-connected skeleton steps they read R4 = 0.527 (measured
    2026-09-02) -- the staircase, not the bars. Resampled at the chord they
    read ~0.13 over a few dozen votes and do not clear either test."""
    bars = [Region(shape_id=f"B{i}", thread_index=0, thread_number="1",
                   polygon=shapely_rotate(_rect(i * 4.0, 0.0, 0.3, 1.8),
                                          i * 45.0, origin="centroid"),
                   area_mm2=1.0) for i in range(4)]
    votes = _fourfold_votes(bars)
    assert votes is not None
    resultant, _n_eff, _axis = votes
    assert resultant < SATIN_HOUSE_FOURFOLD_MIN_R, resultant
    assert _cluster_house_angle_deg(bars) is None


def test_two_orthogonal_families_get_the_bisector():
    """Block lettering whose bars balance its stems has NO dominant direction
    in doubled-angle space -- a vertical votes at 180 deg, a horizontal at 0,
    and they cancel however much lettering there is. On Kent's Hotel Fremont
    wordmark (twelve slab-serif capitals, 112 mm of vertical skeleton against
    44 mm of horizontal) the doubled test read nR^2 = 4.7 against 6.9 and
    rejected the whole word, so every bar sewed at its own angle.

    Four-fold space sees the structure the doubled space cancels: that same
    word reads nR4^2 = 53.1. The answer is the BISECTOR of the two families,
    not the perpendicular to the stems: at 0 deg every horizontal is 90 deg
    off the house and `_clamp_to_span` flips it to +/-45 on tangent noise,
    which rendered worse than no house angle at all. At 45 deg nothing is
    clamped and every stroke agrees.

    Fixture: a synthetic slab-serif row. Each glyph is a vertical stem with a
    top bar and a bottom bar of comparable length -- an I-beam -- so vertical
    and horizontal skeleton lengths are close and the doubled resultant is
    near zero by construction."""
    glyphs = []
    for i in range(6):
        cx = i * 8.0
        stem = _rect(cx, 0.0, 0.8, 6.0)
        top = _rect(cx, -2.6, 4.0, 0.8)
        bottom = _rect(cx, 2.6, 4.0, 0.8)
        poly = stem.union(top).union(bottom)
        glyphs.append(Region(shape_id=f"I{i}", polygon=poly, thread_index=0,
                             thread_number="1", area_mm2=poly.area))
    house = _cluster_house_angle_deg(glyphs)

    assert house is not None, "two orthogonal families were not seen"
    off = abs(_circ_delta_deg(SATIN_HOUSE_BISECTOR_DEG, house))
    assert off < 3.0, f"expected the bisector, got {house:.1f} deg"

    # And it TRACKS the artwork: rotate the row 20 deg and the bisector
    # rotates with it, because both families rotated together.
    turned = _rotated(glyphs, 20.0, origin=(0.0, 0.0))
    house_t = _cluster_house_angle_deg(turned)
    assert house_t is not None
    assert abs(_circ_delta_deg(house + 20.0, house_t)) < 3.0, (house, house_t)


def test_the_bisector_does_not_flip_when_the_axis_wraps_at_90():
    """The family axis is only defined mod 90, so 0.1 deg and 89.9 deg are
    the same upright lettering -- and "axis + 45" would hand them 45 and 135,
    mirror-image slants decided by which side of the wrap the tangent noise
    fell. Measured on two real wordmarks the same day (2026-09-02): drone's
    THERMAL read 0.1 -> 45.1, Hotel Fremont read 89.4 -> 134.4. The bisector
    nearer the convention is the stable choice."""
    assert abs(_circ_delta_deg(45.0, _bisector_deg(0.1))) < 0.2
    assert abs(_circ_delta_deg(45.0, _bisector_deg(89.4))) < 1.0, _bisector_deg(89.4)
    assert abs(_circ_delta_deg(45.0, _bisector_deg(89.9))) < 0.2
    # A tilted word tracks its tilt on the same side of the convention.
    assert abs(_circ_delta_deg(65.0, _bisector_deg(20.0))) < 1e-9
    assert abs(_circ_delta_deg(25.0, _bisector_deg(70.0))) < 1e-9


def test_one_dominant_direction_still_wins_over_the_bisector():
    """The doubled reading is tried FIRST, so a stems-dominated word keeps
    the perpendicular-to-stems answer it always had: the four-fold reading
    never gets a say when the first one is significant. Vertical stems ->
    a horizontal (0 deg) cross, not a 45 deg one."""
    regions = _row("S", 6)
    house = _cluster_house_angle_deg(regions)
    assert house is not None
    assert abs(_circ_delta_deg(0.0, house)) < 3.0, house


def test_a_word_gets_the_house_angle_on_BOTH_tiers():
    """A word does not get to pick its tier — `classify_ribbon` routes each
    letter on its own width, so one wordmark's glyphs routinely split across
    satin and fill. On Kent's Becker logo 7 of 11 lettering regions sew as
    fill, and that is the half his complaint names."""
    regions = _row("L", 5, w=1.2, h=12.0)
    set_lettering_house_angle(regions, _P)

    for r in regions:
        assert "satin_angle_deg" in r.meta
        assert "fill_angle_deg" in r.meta
        assert r.meta["fill_angle_deg"] == r.meta["satin_angle_deg"]


def test_a_fill_angle_already_set_on_a_shape_is_not_overwritten():
    """`fill_angle_deg` is in `regions.match_and_carry`'s carry-forward tuple,
    so unlike the satin key it really can arrive carrying operator intent from
    a previous generation. Deriving must never overwrite that."""
    regions = _row("L", 5, w=1.2, h=12.0)
    regions[1].meta["fill_angle_deg"] = 33.0
    set_lettering_house_angle(regions, _P)

    assert regions[1].meta["fill_angle_deg"] == 33.0
    assert regions[1].meta["satin_angle_deg"] != 33.0
    others = {r.meta["fill_angle_deg"] for r in regions if r is not regions[1]}
    assert len(others) == 1 and 33.0 not in others
