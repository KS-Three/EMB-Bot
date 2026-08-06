"""`textcluster.detect_text_clusters` — geometry-only "is this a word" tagger.

Fixtures are synthetic rectangles standing in for rescued letter glyphs, at
the scale `test_run_tier.py`'s subline fixture established as realistic: a
1.9 mm-tall subline with letters spaced about 2.3 mm apart (`_subline_image`,
20 px steps at 8.75 px/mm). Every candidate here carries
`meta["rescued_small_shape"] = True` by hand — this module trusts that flag,
it does not re-derive it (Step 1 already owns that decision).
"""
from __future__ import annotations

import random

import numpy as np
import pytest
from shapely.geometry import Polygon

from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.textcluster import (
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


def _letter(shape_id: str, cx: float, cy: float, w: float = 0.9, h: float = 1.8,
            rescued: bool = True) -> Region:
    meta = {"rescued_small_shape": True} if rescued else {}
    poly = _rect(cx, cy, w, h)
    return Region(shape_id=shape_id, polygon=poly, thread_index=0,
                  thread_number="1", area_mm2=poly.area, meta=meta)


def _row(prefix: str, n: int, x0: float = 0.0, y: float = 0.0,
         spacing: float = 2.3, w: float = 0.9, h: float = 1.8) -> list[Region]:
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
    big = _row("G", 4, x0=0.0, y=6.0, w=4.0, h=8.0)  # 4-5x the small letters
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

    detect_text_clusters(regions, _P)
    assert all(r.meta.get("text_cluster_id") for r in regions), \
        "fixture must actually form one cluster for this test to mean anything"

    before_stroke = [_stroke_mm_of(p) for p in before_polys]
    assert all(v is not None for v in before_stroke)

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
    widths = [0.7, 0.8, 0.9, 1.0, 1.1]
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


def test_regularize_skips_a_member_already_close_to_the_cluster_target():
    """A member within `_REGULARIZE_SKIP_TOLERANCE` of the cluster's target
    half-width is left completely untouched — the real-fixture case (13 of
    the benchmark subline's 14 members measured within +-11%, see the module
    docstring), reproduced as a minimal synthetic cluster: four letters at
    an identical width (the exact median, zero deviation) plus one genuine
    outlier far enough off to still need correction."""
    regions = _row_varied_width("W", [0.9, 0.9, 0.9, 0.9, 1.6])
    detect_text_clusters(regions, _P)
    assert all(r.meta.get("text_cluster_id") for r in regions)

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
    detect_text_clusters(regions, _P)
    assert all(r.meta.get("text_cluster_id") for r in regions), \
        "fixture must form one cluster for this test to mean anything"

    original_coords = (list(holed.polygon.exterior.coords),
                        [list(r.coords) for r in holed.polygon.interiors])

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
