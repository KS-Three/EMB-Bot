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
from skimage.color import deltaE_ciede2000
from skimage.morphology import skeletonize

from . import machine
from .config import PipelineConfig
from .stage1_prep import Prep
from .stage2_quantize import _quantize_population
from .threads import chart_for, rgb_to_lab

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
    # How many of the LEADING labels are the lightness read's
    # (`find_dark_thin_ink`): those regions get the colour cap's dark-ink
    # rule (`stage4_vectorize.enforce_color_cap`). 0 for the quantiser read.
    dark: int = 0


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


# --- dark ink on a shaded ground (`cfg.keep_dark_thin_strokes`) ------------
# `find_thin_ink` above reads the artwork with the flat lane's quantiser, so
# a stroke only exists for it when k-means gives the stroke its OWN colour.
# Hand lettering drawn on a shaded body does not get one: on Kent's cartoon
# of 2026-10-27 the pen ink on a grey-green pot reads Lab (43.7, -1.0, 20.5)
# against the pot's (66.1, -4.1, 18.6) -- 21.5 dE00 apart, and 0.5-0.75 mm
# wide (4-6 px at the 8 px/mm working grid). k-means folds that into the
# pot, the superpixels straddle it, and `MERGE_DELTAE00_THRESH` (26.0, on
# superpixel MEANS) absorbs what is left: one letter of five sewed, half of
# another. `tools.thin_strokes` saw 0 lost strokes, because its reader is
# this same quantiser.
#
# `find_dark_thin_ink` reads LIGHTNESS instead of colour: a black-hat on L*
# (the closing minus the image) is the depth of every dark feature that fits
# inside the structuring element, so a stroke under the detail floor comes
# out at its full contrast whatever the ground's colour or shading, and a
# shaded ground -- which the closing follows -- comes out at zero. The three
# tests after that are the thin population's own, through
# `iter_thin_components` (width under `cfg.min_detail_mm` at p90, at least
# `THIN_INK_MIN_PX`, length at least half a run loop), then this module's
# one-ground rule read on the raster rather than on labels (`_dark_ring`).
# Unlike the quantiser read, the kept pixels do NOT leave the SEEDS
# foreground: the merge runs as it always has, and `absorbed_dark_ink` then
# carves out only the strokes it folded into their ground (a stroke with a
# merged label of its own already survived and is left alone). Measured on
# the cartoon: taking the pixels out before SEEDS also took the nose and
# toe lines out of the main population, the palette's medoids moved and
# the pot split into two threads (34 -> 68 regions); carving after the
# merge changed the letters and nothing else (34 -> 37 regions).
#
# Measured on that cartoon, 80 mm hat_front (`tools.fremont_triage.
# studio_request` through the service's own decode and `_parse_config`):
#   * kernel `2 * floor_px + 1` (25 px): at the floor itself (13 px) the pot's
#     outline splits into pieces the ring test has to refuse one by one; at
#     twice it the five letters are five components and nothing else inside
#     the pot clears the floors.
#   * `DARK_INK_DEPTH_L` (pixel membership, L* units): at 6 the letters bloat
#     (p90 width 7.2-8.0 px from 6.0-6.4) and JPEG ripples on the body
#     qualify (2.7-3.7 dE00 against their ring); at 8 and 10 the same five
#     components come out with the same widths within 0.4 px. 8 keeps one
#     more pixel of edge than 10.
#   * `DARK_INK_MIN_CONTRAST_DE00` (component median against ring median):
#     the five letters read 12.1-25.9, the toe lines 19.9, the nose 32.6; the
#     ripples that pass the pixel test read 2.7-3.7 and nothing sits between.
#   * `DARK_INK_GROUND_DE00`: the ring (2 px wide, 2 px out) is "one ground"
#     when `THIN_INK_GROUND_SHARE` of it sits within this of its own median,
#     pixels outside the foreground counted against. 13.0 is the boundary-
#     contrast rule's absolute local threshold (`stage2_photo_segment.
#     BOUNDARY_CONTRAST_MERGE_FACTOR`'s numerator, MERGE_DELTAE00_THRESH / 2),
#     the one number that module already holds for "the same region". The
#     letters' rings read 0.97-1.00; the cartoon's outlines, with body on one
#     side and background or a different panel on the other, 0.01-0.46.
# The constants are raster-and-colour quantities, not stitch ones: nothing
# here needs a sew-out (ROADMAP gate 1).
#
# A COUNTER is not ink (2026-10-28, PR #1162's sheet on `summit_badge`): the
# dark ground inside the lower bowl of the S of SUMMIT passed every test
# above -- it is dark, thin, ringed by one light ground -- because the
# ground ringing it IS the letter. The quantiser read (`find_thin_ink`) had
# already taken the S out of the SEEDS foreground as a thin stroke, so the
# superpixel under the bowl reached across the stroke to the badge's
# background, the merge gave the bowl the background's label, and
# `absorbed_dark_ink` carved it out as a 2.6 mm2 "stroke" in the background's
# own thread (nothing new visible), while the background lost two blend
# bands with it (see `stage6_blend.blend_fill`). `find_dark_thin_ink` now
# takes the thin population's mask as `glyphs`: a component whose one ground
# (the ring pixels within `DARK_INK_GROUND_DE00` of the ring's median) is
# itself thin-population pixels at `THIN_INK_GROUND_SHARE` or more is ringed
# by a glyph, not drawn on a ground, and is refused. Measured on summit at
# 80 mm: the bowl's ring is 251 foreground pixels, 190 of them the S (an
# 11.5 mm2 thin component) and 61 the background at the bowl's open side;
# the one-ground pixels are the 190, all of them thin population (share 1.0).
# The cartoon's letters sit on the pot, which no thin read owns (share 0).
# The pipeline's own thinness read is the "letter" here -- no OCR, no new
# width constant; a letter wider than `cfg.min_detail_mm` is not in the
# thin population and keeps its own merged label, so its counter is never
# absorbed in the first place.
DARK_INK_DEPTH_L = 8.0
DARK_INK_MIN_CONTRAST_DE00 = 10.0
DARK_INK_GROUND_DE00 = 13.0
_DARK_INK_GUARD_PX = 2
# A STRAY (`cfg.dark_ink_refuse_strays`, built OFF 2026-10-28 on Kent's
# "queue refusal" on PR #1172): a kept component whose ring reaches the
# artwork's edge -- guard plus ring, so the one-ground test ran on a part
# ring -- or whose pixels are not, as a whole, under the ring the way the
# black-hat asked of each one. Measured on the 30 reads of #1172's sheet
# (the owl's 16, the Fremont patch's 14, 80 mm left_chest, the engine's own
# raster): the 10 reads judged "not ink" there are the 10 components within
# 1 px of the frame; the 16 ink reads sit 6-170 px in (the patch's keylines
# at 6, the nearest). Every one of the 30 has 0.75-1.0 of its pixels
# `DARK_INK_DEPTH_L` under its ring's median, so the share clause fires on
# none of them: it is the tripwire for a bimodal component the median test
# lets through, at the majority `absorbed_dark_ink` already asks for.
DARK_INK_EDGE_PX = _DARK_INK_GUARD_PX + _RING_PX
DARK_INK_STRAY_SHARE = 0.5


def stray_clause(bbox: tuple[int, int, int, int], art_bbox: tuple[int, int, int, int],
                 comp_l: np.ndarray, ground_l: float) -> str | None:
    """Which stray clause refuses a kept dark component: "edge" when its
    bbox (x, y, w, h) lies within `DARK_INK_EDGE_PX` of `art_bbox` (x0, y0,
    x1, y1 exclusive), "ground" when fewer than `DARK_INK_STRAY_SHARE` of
    `comp_l` (its pixels' L*) sit `DARK_INK_DEPTH_L` under `ground_l`; None
    when neither fires."""
    bx, by, bw, bh = bbox
    ax0, ay0, ax1, ay1 = art_bbox
    if min(bx - ax0, by - ay0, ax1 - (bx + bw), ay1 - (by + bh)) < DARK_INK_EDGE_PX:
        return "edge"
    if float(np.mean(comp_l < ground_l - DARK_INK_DEPTH_L)) < DARK_INK_STRAY_SHARE:
        return "ground"
    return None


def _dark_ring(lab: np.ndarray, valid: np.ndarray, comp: np.ndarray,
               y0: int, x0: int, glyphs: np.ndarray | None = None
               ) -> tuple[np.ndarray | None, int, np.ndarray | None]:
    """The Lab of the foreground pixels in the `_RING_PX`-wide ring that sits
    `_DARK_INK_GUARD_PX` outside `comp` (a crop placed at (y0, x0)), the
    ring's full pixel count, background included, and -- when `glyphs` is
    given -- a bool per returned pixel saying whether it lies in `glyphs`
    (None otherwise). The guard keeps the stroke's own anti-alias fringe out
    of the ground sample."""
    h, w = valid.shape
    ch, cw = comp.shape
    pad = _DARK_INK_GUARD_PX + _RING_PX
    wy0, wx0 = max(0, y0 - pad), max(0, x0 - pad)
    wy1, wx1 = min(h, y0 + ch + pad), min(w, x0 + cw + pad)
    window = np.zeros((wy1 - wy0, wx1 - wx0), np.uint8)
    window[y0 - wy0:y0 - wy0 + ch, x0 - wx0:x0 - wx0 + cw] = comp
    kg = np.ones((2 * _DARK_INK_GUARD_PX + 1,) * 2, np.uint8)
    guarded = cv2.dilate(window, kg)
    kr = np.ones((2 * _RING_PX + 1,) * 2, np.uint8)
    ring = (cv2.dilate(guarded, kr) > 0) & (guarded == 0)
    n = int(ring.sum())
    if n == 0:
        return None, 0, None
    inside = ring & valid[wy0:wy1, wx0:wx1]
    if not inside.any():
        return None, n, None
    in_glyph = None if glyphs is None else glyphs[wy0:wy1, wx0:wx1][inside]
    return lab[wy0:wy1, wx0:wx1][inside], n, in_glyph


def find_dark_thin_ink(p: Prep, cfg: PipelineConfig, valid: np.ndarray,
                       glyphs: np.ndarray | None = None) -> ThinInk | None:
    """Dark thin strokes on whatever ground they are drawn on, inside `valid`
    (the photo lane's foreground with the enclosed population out), or None
    when nothing qualifies -- the caller's path is then byte-identical to the
    flag being off. The caller carves them out AFTER its merge, and only the
    ones the merge absorbed (`absorbed_dark_ink`).

    `glyphs` is the thin population's mask (`find_thin_ink(...).mask`, read on
    the same `valid`), or None: a component whose one ground is made of those
    pixels is a glyph's COUNTER, not a stroke, and is refused (the module
    comment above `DARK_INK_DEPTH_L` has the summit measurement). None keeps
    every component the tests below keep.

    `cfg.dark_ink_refuse_strays` (OFF) adds `stray_clause` after the contrast
    test: a component at the artwork's edge, or not under its ring as a whole,
    is refused.

    The kept components are grouped into inks (`_group_inks`) and each ink
    wears the chart spool nearest its pixel-weighted mean colour
    (`Chart.snap_palette`, the flat quantiser's snap), one label per spool.
    """
    if not valid.any():
        return None
    h, w = p.rgb.shape[:2]
    lab = rgb_to_lab(p.rgb.reshape(-1, 3)).reshape(h, w, 3)
    lightness = np.ascontiguousarray(lab[..., 0], dtype=np.float32)
    floor_px = cfg.min_detail_mm * p.px_per_mm
    k = 2 * int(round(floor_px)) + 1
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (k, k))
    depth = cv2.morphologyEx(lightness, cv2.MORPH_BLACKHAT, kernel)
    dark = (depth > DARK_INK_DEPTH_L) & valid
    if not dark.any():
        return None
    labels = np.where(dark, 0, -1).astype(np.int32)
    kept: list[tuple[ThinComponent, np.ndarray, np.ndarray]] = []   # component, ink Lab, its RGB pixels
    for t in iter_thin_components(labels, 1, p.px_per_mm, cfg, ground_test=False):
        bx, by, bw, bh = t.bbox
        ring_lab, n_ring, in_glyph = _dark_ring(lab, valid, t.comp, by, bx, glyphs)
        if ring_lab is None:
            continue
        ground = np.median(ring_lab, axis=0)
        same = deltaE_ciede2000(ring_lab, np.broadcast_to(ground, ring_lab.shape)) <= DARK_INK_GROUND_DE00
        if float(same.sum()) / float(n_ring) < THIN_INK_GROUND_SHARE:
            continue
        if in_glyph is not None and same.any() and is_counter(same, in_glyph):
            continue
        crop = (slice(by, by + bh), slice(bx, bx + bw))
        ink = np.median(lab[crop][t.comp], axis=0)
        if ink[0] >= ground[0]:
            continue
        if float(deltaE_ciede2000(ink.reshape(1, 3), ground.reshape(1, 3))[0]) < DARK_INK_MIN_CONTRAST_DE00:
            continue
        if cfg.dark_ink_refuse_strays and stray_clause(t.bbox, p.art_bbox, lab[crop][t.comp][:, 0], float(ground[0])):
            continue
        kept.append((t, ink, p.rgb[crop][t.comp].astype(np.float64)))
    if not kept:
        return None
    # One INK per colour group, snapped once from the group's pixel-weighted
    # mean, rather than one spool per stroke: a pen's ink reads lighter where
    # the ground under it is lighter (the five letters' medians span L* 30 to
    # 47 on the cartoon, and snapped one by one they wore four spools), and
    # the flat quantiser the thin population snaps from would have given one
    # cluster to all of them. Two strokes are one ink when their medians sit
    # within `DARK_INK_GROUND_DE00` of each other, linked transitively -- the
    # same tolerance the ring test calls one ground.
    inks = _group_inks([ink for _, ink, _ in kept])
    chart = chart_for(cfg)
    group_rgb = []
    for members in inks:
        px = [kept[i][2] for i in members]
        group_rgb.append(np.concatenate(px, axis=0).mean(axis=0))
    snapped = chart.snap_palette(np.array(group_rgb, dtype=np.float64))
    spools = sorted(set(snapped))
    mask = np.zeros((h, w), bool)
    out = np.full((h, w), -1, np.int32)
    length_px = 0.0
    for members, spool in zip(inks, snapped):
        for i in members:
            t = kept[i][0]
            bx, by, bw, bh = t.bbox
            crop = (slice(by, by + bh), slice(bx, bx + bw))
            mask[crop] |= t.comp
            out[crop][t.comp] = spools.index(spool)
            length_px += t.length_px
    return ThinInk(mask=mask, labels=out, spools=spools, components=len(kept),
                   length_mm=length_px / p.px_per_mm, dark=len(spools))


def is_counter(same: np.ndarray, in_glyph: np.ndarray) -> bool:
    """Is the one ground round a dark component a glyph? `same` marks the
    ring pixels that make up the ground (within `DARK_INK_GROUND_DE00` of the
    ring's median), `in_glyph` the ring pixels the thin population owns; the
    ground is a glyph when the thin population holds `THIN_INK_GROUND_SHARE`
    of it -- the same majority the one-ground rule itself asks for."""
    return float(np.count_nonzero(same & in_glyph)) / float(np.count_nonzero(same)) >= THIN_INK_GROUND_SHARE


def _group_inks(medians: list[np.ndarray]) -> list[list[int]]:
    """Single-linkage groups of component indices whose median Labs sit
    within `DARK_INK_GROUND_DE00` (CIEDE2000) of a member; each group in
    first-seen order, members ascending."""
    n = len(medians)
    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    if n > 1:
        labs = np.array(medians, dtype=np.float64)
        for i in range(n - 1):
            d = deltaE_ciede2000(np.broadcast_to(labs[i], (n - i - 1, 3)), labs[i + 1:])
            for j in np.nonzero(d <= DARK_INK_GROUND_DE00)[0]:
                a, b = find(i), find(int(j) + i + 1)
                if a != b:
                    parent[max(a, b)] = min(a, b)
    groups: dict[int, list[int]] = {}
    for i in range(n):
        groups.setdefault(find(i), []).append(i)
    return [groups[k] for k in sorted(groups)]


def merge_thin_ink(a: ThinInk | None, b: ThinInk | None) -> ThinInk | None:
    """Two populations as one label block: `b`'s labels after `a`'s. The
    callers hand over DISJOINT masks (each is found inside the foreground the
    other already left)."""
    if a is None:
        return b
    if b is None:
        return a
    labels = a.labels.copy()
    in_b = b.labels >= 0
    labels[in_b] = b.labels[in_b] + len(a.spools)
    return ThinInk(mask=a.mask | b.mask, labels=labels, spools=a.spools + b.spools,
                   components=a.components + b.components,
                   length_mm=a.length_mm + b.length_mm,
                   # `a`'s dark labels lead; `b`'s count only when every label
                   # of `a` is dark, so the dark block stays one leading run.
                   dark=a.dark + (b.dark if a.dark == len(a.spools) else 0))


def absorbed_dark_ink(dark: ThinInk, merged: np.ndarray, base_valid: np.ndarray) -> ThinInk | None:
    """The components of `dark` that the merge folded into their ground, as
    a population of their own; None when every one survived.

    A component survived when the merged label most of its foreground pixels
    carry is its OWN -- at least half of that label's foreground pixels lie
    inside the component. The cartoon's nose and toe lines are such labels
    (kept on their contrast, as on every run before this flag) and are left
    exactly as they are. A component whose majority label is a ground's (the
    pot's: 0.4% of that label inside the letter), or whose pixels the
    quantiser read already owns (none left in `base_valid`), is absorbed."""
    n, cc, stats, _ = cv2.connectedComponentsWithStats(dark.mask.astype(np.uint8), connectivity=8)
    totals = np.bincount(merged[base_valid].astype(np.int64)) if base_valid.any() else np.zeros(1, np.int64)
    keep = np.zeros_like(dark.mask)
    for c in range(1, n):
        bx, by, bw, bh, _a = (int(v) for v in stats[c, :5])
        crop = (slice(by, by + bh), slice(bx, bx + bw))
        comp = cc[crop] == c
        inside = merged[crop][comp & base_valid[crop]].astype(np.int64)
        if inside.size:
            label = int(np.bincount(inside).argmax())
            own = float(np.count_nonzero(inside == label)) / float(totals[label])
            if own >= 0.5:
                continue
        keep[crop] |= comp
    if not keep.any():
        return None
    return _restricted(dark, keep)


def thin_without(thin: ThinInk | None, mask: np.ndarray) -> ThinInk | None:
    """`thin` with the pixels of `mask` taken out of it (labels compacted to
    the spools still used); None when nothing is left, or was."""
    if thin is None:
        return None
    keep = thin.mask & ~mask
    if not keep.any():
        return None
    return _restricted(thin, keep)


def _restricted(thin: ThinInk, keep: np.ndarray) -> ThinInk:
    used = sorted(set(int(v) for v in np.unique(thin.labels[keep])))
    labels = np.full(thin.labels.shape, -1, np.int32)
    for new, old in enumerate(used):
        labels[keep & (thin.labels == old)] = new
    n, _cc, _st, _ = cv2.connectedComponentsWithStats(keep.astype(np.uint8), connectivity=8)
    # Length pro-rated by pixel share: a report's number, not a gate's.
    return ThinInk(mask=keep, labels=labels, spools=[thin.spools[o] for o in used],
                   components=n - 1,
                   length_mm=thin.length_mm * float(keep.sum()) / float(thin.mask.sum()),
                   dark=sum(1 for o in used if o < thin.dark))


# `cfg.dark_ink_bean`'s gate: the widest thread contrast, ink to ground, at
# which a dark read is a pen line and sews as a bean. Read thread to thread
# where the tag is written (before the colour cap), measured 2026-10-28: pen
# lines 9.0 (HUNNY, 0454 on the pot's 0763; the cap later moves it to 1233,
# 17.8), 19.0 (the Fremont patch's Stone), 26.7 (Fremont's Wild Rice rope
# and tagline), 27.7 (the synthetic pen, whose PIXELS sit 21.5 apart: thread
# snapping widens a pair by several dE00, so the merge's own 26.0 is too
# tight); designed lettering 100.0 (the Fremont wordmark, Black on White,
# which sewed as hairline skeletons). A CANDIDATE set in that gap; the owl's
# 24.5-65.3 and Bridge's 43.9 sit inside it and are judged on the sheet.
BEAN_MAX_GROUND_DE00 = 50.0


def _thread_de00(a: int, b: int) -> float:
    from .threads import CHART
    la, lb = (rgb_to_lab(np.array([CHART[i].rgb], float)) for i in (a, b))
    return float(deltaE_ciede2000(la, lb)[0])


def _ground_of(stroke, grounds):
    """The shape `stroke` is written on: the one whose OUTLINE (holes
    ignored -- the stroke sits in a hole it cut) covers most of it, at
    least half; else None."""
    from shapely.geometry import Polygon

    best, best_a = None, 0.0
    for g in grounds:
        shell = Polygon(g.polygon.exterior) if isinstance(g.polygon, Polygon) else g.polygon
        a = shell.intersection(stroke.polygon).area
        if a > best_a:
            best, best_a = g, a
    return best if best is not None and best_a >= 0.5 * stroke.polygon.area else None


def bean_dark_ink(regions) -> int:
    """`cfg.dark_ink_bean`: the dark read's strokes sew as a bean ON their
    ground, the way the reference digitizer sews a drawn line
    (`bean_rule`). Each `meta["dark_ink"]` region the review left on "auto"
    gets its polygon's skeleton as bean spines (`beanletters.BEAN_LETTER_KEY`,
    the path stage 7 sews as a bean along the stroke). Its ground keeps the
    hole: stage 5's `ground_under` sews the ground through under a bean
    letter, and a ground closed here first would be "a colour already down"
    that clips the stroke to nothing. The ground is untagged as lettering.

    Only a PEN LINE goes: a stroke on a ground (`_ground_of`) whose thread
    sits within `BEAN_MAX_GROUND_DE00` of the ground's. Above it the ink is
    designed lettering that only the superpixel mean absorbed -- the Fremont
    wordmark, Black on White at 100 dE00, sewed as hairline skeletons ON --
    and sews as it did. Returns the number of strokes tagged."""
    from shapely.geometry import Polygon

    from .beanletters import BEAN_LETTER_KEY
    from .shapefield import build_shape_field
    from .textcluster import _skeleton_chains_mm

    grounds = [r for r in regions if not r.meta.get("dark_ink") and r.polygon is not None]
    tagged = 0
    for r in regions:
        if (not r.meta.get("dark_ink") or str(r.meta.get("tier", "auto")).lower() != "auto"
                or not isinstance(r.polygon, Polygon)):
            continue
        g = _ground_of(r, grounds)
        if g is None or _thread_de00(r.thread_index, g.thread_index) > BEAN_MAX_GROUND_DE00:
            continue
        field = build_shape_field(r.polygon)
        spines = _skeleton_chains_mm(field) if field is not None else []
        if not spines:
            continue
        r.meta[BEAN_LETTER_KEY] = spines
        # The ground the ink is written on, not a letter of it. The
        # house-angle group (`textcluster`, `setdefault`) took the Pooh pot
        # into the Column lane, which its letter holes defeated only while
        # they were holes; sewn through, it was one 37 mm satin.
        g.meta["lettering_group"] = False
        tagged += 1
    return tagged


def ink_after_ground(regions):
    """`cfg.dark_ink_bean`, at plan time: a bean stroke (`bean_dark_ink`)
    whose ground (`_ground_of`) sews in the same or a later layer moves to
    a layer of its own right after the ground's -- the shape
    `silhouette_underfill` gives a rider -- because stage 5 sews a ground
    through only under a LATER bean letter. Regions as copies, renumbered;
    nothing to move: the input list itself."""
    from dataclasses import replace

    from .beanletters import BEAN_LETTER_KEY

    ink = [r for r in regions if r.meta.get("dark_ink") and r.meta.get(BEAN_LETTER_KEY)
           and r.meta.get("stitched", True)]
    grounds = [r for r in regions if not r.meta.get("dark_ink") and r.meta.get("stitched", True)
               and r.polygon is not None]
    to: dict[str, tuple] = {}
    for b in ink:
        g = _ground_of(b, grounds)
        if g is not None and g.meta["layer"] >= b.meta["layer"]:
            to[b.shape_id] = ("ink", g.meta["layer"], b.thread_index)
    if not to:
        return regions
    order = sorted({r.meta["layer"] for r in regions})
    for key in sorted(set(to.values()), key=lambda k: (k[1], k[2]), reverse=True):
        order.insert(order.index(key[1]) + 1, key)
    renum = {L: i for i, L in enumerate(order)}

    def layer_of(r):
        return renum[to.get(r.shape_id, r.meta["layer"])]
    return [replace(r, meta={**r.meta, "layer": layer_of(r)})
            for _i, r in sorted(enumerate(regions), key=lambda t: (layer_of(t[1]), t[0]))]
