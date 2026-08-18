"""A connected chain of small regions must not absorb itself to nothing.

stage3_segment.resolve_small_regions tests each region against the
~2.25 mm^2 floor (cfg.min_detail_mm ** 2) INDIVIDUALLY, then absorbs a
small region into its best halo-share neighbour. When a large structure
arrives fragmented into sub-threshold pieces — the canonical case is a
gradient-filled ring quantised into alternating-colour arc segments —
every piece is "small", every piece's best neighbour is another doomed
piece, and the chain annihilates: measured 2026-08-17, an 84-segment
checkered ring (each segment ~1.80 mm^2, the whole ring 172 mm^2 and
40 mm across) digitised to ZERO sewn regions, with only advisory
ABSORBED_SMALL_SHAPES / EMPTY_THREAD_LAYER warnings to show for it.

The individually-small test is blind to the union: 84 mutually-adjacent
"details" that together form one connected 172 mm^2 shape are not detail.
A fix should size-test connected chains of small same-fate regions as a
unit (or cap total absorbed area) — design pending Kent, see
docs/shape-fidelity-findings-2026-08-17.md.

xfail strict=True per the test_classifier_scale_invariance precedent:
this test turning green IS the acceptance criterion for the fix, and a
silent pass must fail the suite so the xfail gets removed deliberately.
"""
import math

import numpy as np
import pytest
from PIL import Image
from shapely.geometry import Point
from shapely.ops import unary_union

from digitizer_core.config import PipelineConfig
from digitizer_core.pipeline import run_stages


def _checker_ring_png(path, px_mm=5.0):
    """Ring r=20 mm, 1.2 mm wide, ~1.5 mm arc segments in two colours.

    Every segment lands ~1.80 mm^2 — under the 2.25 mm^2 floor — with an
    other-colour halo neighbour on both sides. This is the shape a smooth
    gradient ring takes after quantisation bands it.
    """
    size = int(56 * px_mm)
    c = size / 2
    r_mid, half_w = 20 * px_mm, 0.6 * px_mm
    n_seg = int(round(2 * math.pi * 20 / 1.5))
    img = np.full((size, size, 3), 255, np.uint8)
    yy, xx = np.mgrid[:size, :size]
    rr = np.hypot(yy - c, xx - c)
    theta = np.arctan2(yy - c, xx - c) % (2 * math.pi)
    ring = np.abs(rr - r_mid) <= half_w
    seg = (theta / (2 * math.pi) * n_seg).astype(int) % 2
    img[ring & (seg == 0)] = (200, 30, 30)
    img[ring & (seg == 1)] = (30, 40, 160)
    Image.fromarray(img).save(path)


@pytest.mark.xfail(
    strict=True,
    reason="chained absorb annihilates a fragmented ring; fix design pending "
    "(docs/shape-fidelity-findings-2026-08-17.md)",
)
def test_fragmented_ring_survives_small_region_cleanup(tmp_path):
    p = tmp_path / "checker_ring.png"
    _checker_ring_png(p)
    cfg = PipelineConfig()
    cfg.target_width_mm = 44.0
    res = run_stages(str(p), cfg)

    sewn = [r for r in res.regions if not (r.meta or {}).get("enclosed_background")]
    assert sewn, "every sewn region was absorbed/dropped — the ring vanished"

    # The surviving geometry must still BE the ring: compare against the
    # ideal annulus in the engine's centred frame (ink bbox 41.2 mm -> 44 mm).
    scale = 44.0 / 41.2
    ideal = Point(0, 0).buffer((20 + 0.6) * scale).difference(
        Point(0, 0).buffer((20 - 0.6) * scale)
    )
    u = unary_union([r.polygon.buffer(0) for r in sewn])
    iou = u.intersection(ideal).area / u.union(ideal).area
    # Merging all 84 segments into ONE colour is an acceptable resolution;
    # losing the annulus is not. 0.3 is far above the measured 0.000 and far
    # below what any ring-preserving outcome produces.
    assert iou > 0.3, f"ring integrity IoU {iou:.3f}"
