"""Thin ink on the photo lane — the third population `cfg.keep_thin_strokes` adds.

PR 3 of `docs/superpowers/plans/2026-09-08-real-logo-lane-and-thin-strokes.md`
(§4c). The gradient and photo lanes segment with SEEDS superpixels of
roughly 47 px a side on Fremont; a 0.4 mm stroke is a quarter of a block,
so its pixels are assigned to a block whose mean colour is the ground, the
RAG merge then compares MEANS, and the stroke is gone before any floor is
consulted. Measured 2026-09-08 (`tools/thin_strokes.py`): routed Fremont
sews its strokes under 0.5 mm at 53% recall, the flat lane's absorb being
the other band's problem (`stage3_segment.resolve_small_regions`).

The precedent is `Prep.enclosed_mask`: enclosed-background pixels are
excluded from SEEDS and quantised as their own population by
`stage2_quantize._quantize_population`, then appended after the base labels.
Thin ink gets the same treatment. `find_thin_ink` runs the flat lane's own
quantiser over the photo lane's foreground (k-means, majority filter,
phantom-blend dissolve, spool snap — the halo pass the gradient lane never
got, defect 27), skeletonises each label, and keeps the connected
components that read as STROKES:

  * thin ALONG ITS WHOLE SKELETON: the full width (twice the distance
    transform on the skeleton — a half-width doubled; `textcluster.py`'s
    docstring names the trap of quoting the radius) under `cfg.min_detail_mm`
    at the 90th percentile, not just the median. A median alone admits a
    GROUND full of lettering: Fremont's white patch is one 1.5-million-pixel
    component whose skeleton threads the gaps between letters, median width
    1.32 mm, 90th percentile 3.77, maximum 7.41 — measured 2026-09-08, and
    it had been counted as a 1,758 mm "stroke" by the first instrument. And
    at least `THIN_INK_MIN_PX` pixels wide — a one- or two-pixel component
    is the raster's anti-alias or compression halo at any resolution, while
    the thinnest stroke the pro widened on Fremont is 0.24 mm = 6.5 px at
    that file's 27 px/mm;
  * skeleton length at least `RUN_MIN_LOOP_MM / 2` — the loop constant
    applied to an open stroke, which a bean run walks there and back (the
    length gate is what separates a stroke from a fragment; no new
    millimetre, both floors already gate the run tier);
  * ON ONE GROUND: the two-pixel ring around the component is dominated by
    a single label (`THIN_INK_GROUND_SHARE`). A stroke drawn on something
    has the same thing on both sides of it; a band a posterised gradient
    leaves between two levels has a different level on each side and is not
    ink, however thin and long. This is the test that keeps the population
    EMPTY on photographs, where every other gate admits highlight rims and
    fur — measured 2026-09-08 over the committed photo fixtures, both arms;
    the numbers are in scope-history's 09-08 entries and this constant's
    comment.

The kept pixels leave `base_valid` before SEEDS runs, so no superpixel
straddles a stroke, and come back as their own label block after the photo
palette (`stage2_photo_segment.kept_masks_to_quant`), wearing the spools
the flat quantiser snapped them to — the same colours `tools/thin_strokes`
reads the artwork with. Stage 4 then treats each component as it treats any
sub-floor mask that reaches it: the real-geometry run-tier test, and the
`rescued_small_shape` tag that is door 1 of the text cluster.

Returns None when nothing qualifies, and the caller's path is then
byte-identical to the flag being off — the invariant the photo goldens pin
for photographs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import cv2
import numpy as np
from skimage.morphology import skeletonize

from . import machine
from .config import PipelineConfig
from .stage1_prep import Prep
from .stage2_quantize import _quantize_population

# A component narrower than this many PIXELS is halo, not ink — a raster
# quantity (the same class as `stage4_vectorize._CURVE_MIN_PX_PER_MM` and
# `tools/thin_strokes._MIN_STROKE_PX`, which found the need: without it the
# "worst lost stroke" on Fremont was a 34.6 mm sliver 0.07 mm = 2 px wide, the
# webp's ringing around the black band quantised to its own label).
THIN_INK_MIN_PX = 3.0
# Fewer skeleton pixels than this is a speck the length floor refuses anyway;
# skipping it early keeps the per-component loop cheap on a photograph's
# thousands of fragments.
_MIN_SKELETON_PX = 3
# The share of the two-pixel ring around a component that one label must
# hold for the component to be a stroke ON that ground rather than a band
# BETWEEN two grounds. Measured 2026-09-08 over the committed photo fixtures
# at 0.6 / 0.75 / 0.9 (scope-history 09-08): see there before moving it.
THIN_INK_GROUND_SHARE = 0.75
_RING_PX = 2


@dataclass
class ThinInk:
    """The thin population: its pixels, their labels and the spools those
    labels wear, plus the two numbers a report wants."""

    mask: np.ndarray          # (H, W) bool
    labels: np.ndarray        # (H, W) int32, -1 outside `mask`; index into `spools`
    spools: list[int]         # chart indices, one per label
    components: int
    length_mm: float


def _link_length_px(skel: np.ndarray) -> float:
    """Length of a 1-px skeleton as the sum of its 8-connected links: one per
    orthogonal neighbour pair, root-two per diagonal pair."""
    s = skel.astype(bool)
    h = np.count_nonzero(s[:, :-1] & s[:, 1:])
    v = np.count_nonzero(s[:-1, :] & s[1:, :])
    d1 = np.count_nonzero(s[:-1, :-1] & s[1:, 1:])
    d2 = np.count_nonzero(s[:-1, 1:] & s[1:, :-1])
    return float(h + v + math.sqrt(2.0) * (d1 + d2))


def ground_share(labels: np.ndarray, comp: np.ndarray, y0: int, x0: int) -> float:
    """The largest share any one label (background's -1 included) holds of
    the `_RING_PX`-wide ring around `comp` (a crop placed at (y0, x0) in
    `labels`' frame). 1.0 for an isolated stroke on one ground, about 0.5
    for a band between two."""
    h, w = labels.shape
    ch, cw = comp.shape
    wy0, wx0 = max(0, y0 - _RING_PX), max(0, x0 - _RING_PX)
    wy1, wx1 = min(h, y0 + ch + _RING_PX), min(w, x0 + cw + _RING_PX)
    window = np.zeros((wy1 - wy0, wx1 - wx0), np.uint8)
    window[y0 - wy0:y0 - wy0 + ch, x0 - wx0:x0 - wx0 + cw] = comp
    k = np.ones((2 * _RING_PX + 1, 2 * _RING_PX + 1), np.uint8)
    ring = (cv2.dilate(window, k) > 0) & (window == 0)
    if not ring.any():
        return 1.0
    vals = labels[wy0:wy1, wx0:wx1][ring]
    _u, counts = np.unique(vals, return_counts=True)
    return float(counts.max()) / float(vals.size)


@dataclass
class ThinComponent:
    """One thin connected component of one label, in raster units."""

    label: int
    bbox: tuple[int, int, int, int]     # x, y, w, h in the label frame
    comp: np.ndarray                    # (h, w) bool crop
    width_px: float                     # median full width along the skeleton
    width_p90_px: float                 # 90th percentile of the same
    length_px: float                    # 8-connected link length of the skeleton
    ground: float                       # `ground_share`


# The width percentile a stroke must be thin at. The median admits a ground
# threaded between letters (see the module docstring); a maximum would refuse
# a real stroke at its junctions and serifs, where the distance transform
# swells for a few pixels. Fremont's real letters read p90 1.04–1.05 against
# medians of 1.03–1.04 (2026-09-08).
THIN_INK_WIDTH_PCT = 90


def iter_thin_components(labels: np.ndarray, n_labels: int, px_per_mm: float,
                         cfg: PipelineConfig, *, ground_test: bool = True,
                         ground_share_min: float = THIN_INK_GROUND_SHARE):
    """Yield every `ThinComponent` in `labels` (int32, -1 outside the
    population, 0..n_labels-1 inside). One test, shared by the engine
    (`find_thin_ink`) and the instrument (`tools/thin_strokes.py`), so the two
    never disagree about what a thin stroke is.

    The floors are the run tier's own: width under `cfg.min_detail_mm` at
    the `THIN_INK_WIDTH_PCT`th percentile along the skeleton and at least
    `THIN_INK_MIN_PX` at the median; skeleton length at least
    `machine.RUN_MIN_LOOP_MM / 2.0`. `ground_test` adds the one-ground rule.
    """
    floor_px = cfg.min_detail_mm * px_per_mm
    min_len_px = (machine.RUN_MIN_LOOP_MM / 2.0) * px_per_mm
    for j in range(n_labels):
        label_mask = labels == j
        if not label_mask.any():
            continue
        # One distance transform and one skeleton per LABEL: components of
        # one label are disjoint, so each one's are the union's restricted.
        dt = cv2.distanceTransform(label_mask.astype(np.uint8), cv2.DIST_L2, 5)
        skel = skeletonize(label_mask)
        n, cc, stats, _ = cv2.connectedComponentsWithStats(label_mask.astype(np.uint8), connectivity=8)
        for c in range(1, n):
            bx, by, bw, bh, _area = (int(v) for v in stats[c, :5])
            comp = cc[by:by + bh, bx:bx + bw] == c
            sk = skel[by:by + bh, bx:bx + bw] & comp
            if int(sk.sum()) < _MIN_SKELETON_PX:
                continue
            widths = 2.0 * dt[by:by + bh, bx:bx + bw][sk]
            width_px = float(np.median(widths))
            width_p90 = float(np.percentile(widths, THIN_INK_WIDTH_PCT))
            if width_p90 >= floor_px or width_px < THIN_INK_MIN_PX:
                continue
            length = _link_length_px(sk)
            if length < min_len_px:
                continue
            share = ground_share(labels, comp, by, bx)
            if ground_test and share < ground_share_min:
                continue
            yield ThinComponent(label=j, bbox=(bx, by, bw, bh), comp=comp, width_px=width_px,
                                width_p90_px=width_p90, length_px=length, ground=share)


def find_thin_ink(p: Prep, cfg: PipelineConfig, valid: np.ndarray, *,
                  ground_test: bool = True,
                  ground_share_min: float = THIN_INK_GROUND_SHARE) -> ThinInk | None:
    """The thin population inside `valid` (the photo lane's foreground with
    the enclosed population already out), or None when nothing qualifies.

    `ground_test=False` drops the one-ground rule — the measurement arm the
    rule was chosen against, kept callable so it stays measurable.
    """
    if not valid.any():
        return None
    h, w = p.rgb.shape[:2]
    flat_rgb = p.rgb.reshape(-1, 3)
    labels, spools, _warnings = _quantize_population(flat_rgb, valid, h, w, cfg, p.bg_edge_rgb)
    ppm = p.px_per_mm
    mask = np.zeros((h, w), bool)
    components = 0
    length_px = 0.0
    for t in iter_thin_components(labels, len(spools), ppm, cfg, ground_test=ground_test,
                                  ground_share_min=ground_share_min):
        bx, by, bw, bh = t.bbox
        mask[by:by + bh, bx:bx + bw] |= t.comp
        components += 1
        length_px += t.length_px
    if components == 0:
        return None
    used = sorted(set(int(v) for v in np.unique(labels[mask])))
    out = np.full((h, w), -1, np.int32)
    for new, old in enumerate(used):
        out[mask & (labels == old)] = new
    return ThinInk(mask=mask, labels=out, spools=[spools[o] for o in used],
                   components=components, length_mm=length_px / ppm)
