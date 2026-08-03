"""Stage 2 (photo path) — SLIC + RAG region former.

`docs/superpowers/plans/2026-08-02-photo-digitizing-step4-region-former.md`,
"## Tests". Five tests: region-forming beats naive per-pixel clustering on a
soft edge, the min-area floor absorbs a deliberately tiny sliver,
determinism, full-pipeline integration through `run_stages()`, and the flat/
gradient lanes staying byte-identical to the pre-change golden (reusing
`test_flat_lane_byte_identical.py`'s own fixture list and snapshot helper
rather than re-implementing it — that file is the record of truth and is
not touched by this change).
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages
from digitizer_core.stage1_prep import prep
from digitizer_core.stage2_photo_segment import segment
from digitizer_core.stage2_quantize import quantize
from digitizer_core.stage3_segment import ClassicalSegmenter
from digitizer_core.warnings_codes import ABSORBED_SMALL_SHAPES, PHOTO_SEGMENT_REGION_COUNT

from .test_flat_lane_byte_identical import GOLDEN, _snapshot

TESTDATA = Path(__file__).resolve().parent.parent / "testdata"
FIXTURE = TESTDATA / "photo" / "region_blobs.png"


def _cfg(**kw) -> PipelineConfig:
    kw.setdefault("target_width_mm", 80.0)
    return PipelineConfig(**kw)


# --- 1. Region-forming beats naive per-pixel clustering on a soft edge ------


def test_region_forming_beats_naive_clustering_on_soft_edges():
    cfg = _cfg()
    p = prep(FIXTURE, cfg)

    q = segment(p, cfg)
    region_count = len(q.thread_indices)
    # A tight, small range: proof the hierarchical merge actually
    # consolidated SLIC's raw output (which measures well over a thousand
    # superpixels on this fixture) rather than just relabeling it.
    assert 0 < region_count < 15, f"expected consolidated regions, got {region_count}"

    # The naive per-pixel path (today's flat-art quantizer) run on the same
    # foreground: connected-component count after its own color clustering,
    # with no spatial merging step at all.
    naive_q = quantize(p, cfg)
    naive_masks = ClassicalSegmenter().segment(naive_q, p, cfg)
    assert len(naive_masks) > 5 * region_count, (
        f"naive clustering only produced {len(naive_masks)} components against "
        f"{region_count} SLIC+RAG regions — the fixture's grain isn't tripping "
        "per-pixel dithering the way this test expects"
    )

    # Cleanliness proxy: a region eroded by 1px should still cover most of
    # its own area. Speckle (salt-and-pepper, no pixel more than 1 away from
    # a differently-labeled one) collapses to near-nothing under erosion; a
    # clean, solid region loses only its outer 1px rim.
    for label in range(region_count):
        mask = (q.labels == label).astype(np.uint8)
        area = int(mask.sum())
        assert area > 0
        eroded = int(cv2.erode(mask, np.ones((3, 3), np.uint8)).sum())
        assert eroded >= 0.5 * area, (
            f"region {label} reads as speckle after erosion ({eroded}/{area} px survived)"
        )


# --- 2. Min-area floor absorbs a deliberately tiny sliver -------------------


def _sliver_image() -> np.ndarray:
    """Two big flat-ish blocks (BGR) plus a deliberately tiny sliver of a
    third, unrelated color straddling the boundary between the red block
    and open background — small enough that no cfg.min_detail_mm floor will
    ever consider it a real detail, and a different enough color that the
    RAG merge step (step 3) would NOT have absorbed it on color grounds
    alone. Only the min-area floor (step 4, color-agnostic: force-merge
    into the longest shared boundary) explains it disappearing.

    Sized deliberately larger than a single-digit-pixel speck: SLIC itself
    (not just the merge/floor steps) already discards anything much smaller
    than its own superpixel granularity by folding it into a neighboring
    superpixel before a RAG node for it ever exists — which would prove
    nothing about THIS module's min-area floor specifically. An 18x18px
    sliver survives as its own SLIC segment (and its own post-merge region)
    at this fixture's resolution, so its disappearance is attributable to
    `resolve_small_regions`, not SLIC's internal cleanup."""
    h, w = 220, 320
    img = np.full((h, w, 3), 255, np.uint8)
    cv2.rectangle(img, (20, 20), (150, 190), (60, 60, 200), -1)    # red block
    cv2.rectangle(img, (160, 20), (290, 190), (200, 60, 60), -1)   # blue block
    cv2.rectangle(img, (140, 90), (158, 108), (60, 200, 60), -1)   # 18x18px green sliver
    return img


def test_min_area_floor_absorbs_a_tiny_sliver():
    # A smaller target_width_mm than the other tests here (still a
    # perfectly ordinary embroidery size) — raises px_per_mm, and with it
    # the min-area floor in PIXEL terms, without changing SLIC's own
    # superpixel granularity (fixed by the canvas's pixel dimensions). That
    # headroom is what lets the sliver above be simultaneously big enough to
    # survive as its own SLIC/RAG region and small enough to be sub-floor.
    cfg = _cfg(target_width_mm=20.0)
    p = prep(_sliver_image(), cfg)
    min_area_px = (cfg.min_detail_mm * p.px_per_mm) ** 2

    q = segment(p, cfg)

    # The sliver's own area (18*18 = 324px, drawn) is a precondition for
    # this test meaning anything — if it isn't actually below the floor,
    # absorption proves nothing.
    assert 324 < min_area_px, "fixture assumption violated: sliver would clear the floor"

    assert any(w["code"] == ABSORBED_SMALL_SHAPES for w in q.warnings), (
        "expected the min-area floor to fire and report an absorption"
    )
    # No surviving region reads as near-pure green (the sliver's own color)
    # at a tiny area — it must have been swallowed into a neighbor, not kept
    # as its own sub-floor region.
    for label in range(len(q.thread_indices)):
        mask = q.labels == label
        area = int(mask.sum())
        if area >= min_area_px:
            continue
        mean_rgb = p.rgb[mask].reshape(-1, 3).mean(axis=0)
        is_greenish = mean_rgb[1] > mean_rgb[0] + 20 and mean_rgb[1] > mean_rgb[2] + 20
        assert not is_greenish, f"the tiny green sliver survived as its own region ({area} px)"


# --- 3. Determinism ----------------------------------------------------------


def test_determinism():
    cfg = _cfg()
    p = prep(FIXTURE, cfg)
    a = segment(p, cfg)
    b = segment(p, cfg)
    assert np.array_equal(a.labels, b.labels)
    assert a.thread_indices == b.thread_indices


# --- 4. Full-pipeline integration -------------------------------------------


def test_full_pipeline_integration_forced_photo_scene():
    cfg = _cfg(forced_class="photo_scene")
    result = run_stages(FIXTURE, cfg)

    assert len(result.regions) > 0
    for r in result.regions:
        assert r.polygon.is_valid
        assert r.polygon.area > 0

    assert any(w["code"] == PHOTO_SEGMENT_REGION_COUNT for w in result.warnings)


# --- 5. Flat/gradient lanes untouched ----------------------------------------


@pytest.mark.parametrize("fixture", sorted(GOLDEN.keys()))
def test_flat_and_gradient_lanes_still_match_golden_after_photo_dispatch(fixture):
    """Re-runs `test_flat_lane_byte_identical.py`'s own fixtures through its
    own snapshot helper — the same invariant that file pins, exercised again
    here as a side effect of `pipeline.py` gaining a third routing branch.
    That file itself is untouched."""
    assert _snapshot(fixture) == GOLDEN[fixture]
