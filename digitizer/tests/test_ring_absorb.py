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

The individually-small test was blind to the union: 84 mutually-adjacent
"details" that together form one connected 172 mm^2 shape are not detail.
Worse, each sliver's best halo-share neighbour is the large BACKGROUND
region it sits on rather than the neighbouring arc, so the ring was
absorbed into the background one segment at a time.

FIXED 2026-08-17 by `_chained_small_regions`: connected chains of
sub-floor regions are size-tested as a unit against the same
`min_area_mm`-derived floor, and a chain that clears it is kept as-is.
This test landed red (xfail strict) and the xfail was removed when the fix
made it green — it is now a regression guard.
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


def test_fragmented_ring_survives_small_region_cleanup(tmp_path):
    p = tmp_path / "checker_ring.png"
    _checker_ring_png(p)
    cfg = PipelineConfig()
    cfg.target_width_mm = 44.0
    # The fixture only exercises chained absorption while its segments stay
    # under the small-region floor, and the margin is thinner than it looks:
    # segments are ~1.80 mm^2 in the source frame but ~2.05 mm^2 once scaled
    # to target_width_mm, only 9% below the 2.25 mm^2 floor. Guard both inputs
    # with RuntimeError, NOT assert — `raises=AssertionError` above would
    # swallow an assert and report a drifted fixture as a clean xfail.
    if cfg.min_detail_mm != 1.5:
        raise RuntimeError(
            f"fixture assumes the 1.5 mm detail floor, got {cfg.min_detail_mm} "
            "— segment areas must be re-derived before this test means anything"
        )
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


def _blocks_config():
    """px_per_mm 2.0 with the 1.5 mm floor -> min_area_px 9.0.

    Chain members are 6 px each (sub-floor on their own); three of them are
    18 px and clear the floor together, which is the whole point of the rescue.
    """
    cfg = PipelineConfig()
    if cfg.min_detail_mm != 1.5:
        raise RuntimeError(
            f"fixture assumes the 1.5 mm detail floor, got {cfg.min_detail_mm}"
        )
    return cfg


def _chain_and_background():
    from digitizer_core.stage3_segment import RegionMask

    def block(rows, cols, layer):
        m = np.zeros((20, 20), bool)
        m[rows[0]:rows[1], cols[0]:cols[1]] = True
        return RegionMask.from_full(m, layer=layer)

    # Three touching 2x3 blocks on ALTERNATING layers, sitting on one big
    # region -- the ring's shape in miniature. Each block's nearest large
    # neighbour is the background, not its fellow fragment, which is the
    # mechanism that annihilated the ring one segment at a time.
    chain = [block((5, 7), (2, 5), 0),
             block((5, 7), (5, 8), 1),
             block((5, 7), (8, 11), 0)]
    background = block((7, 13), (0, 20), 2)
    return chain + [background]


@pytest.mark.parametrize("chain_rescue,expected_kept", [(True, 4), (False, 1)])
def test_chain_rescue_is_gated_per_lane(chain_rescue, expected_kept):
    """The lane gate, measured 2026-08-21.

    `chain_rescue=False` is what both photo segmenters pass. On the photo lane
    quantisation makes sub-floor fragments mutually adjacent everywhere, so
    chaining stops discriminating: on `photo/summit_badge.png` it moved stage 2
    from 34 regions / 12 threads to 46 / 15 and tripled the palette's worst
    excess (max_excess_de00 2.453 -> 7.763). The evidence the rescue shipped on
    (15 pro-parity designs, 13 byte-identical) never covered that lane.

    This asserts the gate itself, not a golden, so removing the argument fails
    with a message that says why instead of as an opaque golden mismatch.
    """
    from digitizer_core.stage3_segment import resolve_small_regions

    regions = _chain_and_background()
    kept, _warnings = resolve_small_regions(
        regions, _blocks_config(), px_per_mm=2.0, chain_rescue=chain_rescue)
    assert len(kept) == expected_kept
