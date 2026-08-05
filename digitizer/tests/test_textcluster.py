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

from shapely.geometry import Polygon

from digitizer_core.regions import Region
from digitizer_core.stage1_prep import Prep
from digitizer_core.textcluster import detect_text_clusters

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
