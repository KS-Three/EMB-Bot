"""Stage 3 — segmentation into regions, behind a swappable interface.

`Segmenter` is the seam the blueprint requires: SAM 2 arrives in build step 2
as another implementation, prompted per-region to REFINE these boundaries.
The color-mask layers stay authoritative for what regions exist — a model is
never trusted to discover regions, because models characteristically miss
thin strokes and small text, exactly the failure-critical parts of a logo.

`ClassicalSegmenter` is connected components per thread layer, and it is the
determinism reference: byte-identical labels for byte-identical input.

Small-region policy (blueprint min detail 1.5 mm): a region below the
sewable area threshold is ABSORBED into whichever neighbor shares the most
boundary with it, or — when it has no neighbor — KEPT for the run tier if it
is at least the size of the mark the thread itself would leave, and DROPPED
only below that. Both drop and absorb are counted and warned — silently
deleting art is the failure mode that erodes trust, and it was exactly small
isolated text (a logo's subline) that the old drop-everything rule deleted.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

from . import machine
from .config import PipelineConfig
from .stage1_prep import Prep
from .stage2_quantize import Quant
from .warnings_codes import (
    ABSORBED_SMALL_SHAPES,
    DROPPED_SMALL_SHAPES,
    EMPTY_THREAD_LAYER,
    warn,
)


@dataclass
class RegionMask:
    """One region's footprint, stored CROPPED to its bounding box.

    Full-frame storage was the pipeline's memory ceiling. A 2800x2100 frame
    yields 1,455 components before the small-region policy culls them to
    ~102, and each used to carry its own (H, W) bool — 8.56 GB held at once,
    which IS the whole peak (measured 2026-08-24: RSS 1,076 -> 8,445 MB
    inside one `segment` call). Cropped, those same 1,455 come to 26.8 MB,
    0.31% of it, and the superlinear MB-per-megapixel curve flattens too.

    `crop` is bbox-tight and `origin` locates it: the footprint in frame
    coordinates is `crop` placed at `origin`, False everywhere else.

    There is deliberately NO `.mask` attribute. The old one was mutated in
    place (`regions[best].mask[box] |= regions[i].mask[box]`), so a property
    handing back a freshly materialized array would have silently dropped
    every absorb — a wrong design, not a crash. Removing the name makes each
    such site fail loudly and get ported on purpose. `union_from` is the
    supported in-place merge; `full_mask()` the explicit escape hatch for
    callers that genuinely need a frame-sized array.
    """
    crop: np.ndarray                 # (h, w) bool — bbox-tight footprint
    origin: tuple[int, int]          # (y0, x0) of `crop` within the frame
    frame_shape: tuple[int, int]     # (H, W) of the frame it belongs to
    layer: int                       # index into Quant.thread_indices
    source: str = "classical"

    @classmethod
    def from_full(cls, mask: np.ndarray, layer: int,
                  source: str = "classical") -> "RegionMask":
        """Crop a frame-sized bool mask on the way in — for producers that
        already hold a full frame (the SAM2 route, tests).

        An all-False mask keeps a 1x1 crop at the origin rather than a
        zero-length one, so `bbox` and the window arithmetic stay total.
        """
        box = _bbox(mask)
        if box is None:
            return cls(crop=np.zeros((1, 1), bool), origin=(0, 0),
                       frame_shape=tuple(mask.shape), layer=layer, source=source)
        y0, x0, y1, x1 = box
        return cls(crop=np.ascontiguousarray(mask[y0:y1, x0:x1]), origin=(y0, x0),
                   frame_shape=tuple(mask.shape), layer=layer, source=source)

    @property
    def area(self) -> int:
        """Set pixels — O(crop), not O(frame), and free at the producer."""
        return int(self.crop.sum())

    @property
    def bbox(self) -> tuple[int, int, int, int]:
        """(y0, x0, y1, x1), y1/x1 exclusive — `_bbox`'s own convention."""
        y0, x0 = self.origin
        h, w = self.crop.shape
        return y0, x0, y0 + h, x0 + w

    def full_mask(self) -> np.ndarray:
        """A frame-sized bool copy. Allocates — never call it in a loop over
        regions, which is the pattern this class exists to kill."""
        m = np.zeros(self.frame_shape, bool)
        m[self.frame_slice()] = self.crop
        return m

    def window(self, wy0: int, wx0: int, wy1: int, wx1: int) -> np.ndarray:
        """This footprint over a window given in FRAME coordinates.

        Returns a (wy1-wy0, wx1-wx0) bool, False where the window falls
        outside the crop — so the neighbour/halo tests keep reading in frame
        coordinates without anyone materializing a frame.
        """
        out = np.zeros((wy1 - wy0, wx1 - wx0), bool)
        y0, x0 = self.origin
        h, w = self.crop.shape
        iy0, ix0 = max(wy0, y0), max(wx0, x0)
        iy1, ix1 = min(wy1, y0 + h), min(wx1, x0 + w)
        if iy0 >= iy1 or ix0 >= ix1:
            return out
        out[iy0 - wy0:iy1 - wy0, ix0 - wx0:ix1 - wx0] = \
            self.crop[iy0 - y0:iy1 - y0, ix0 - x0:ix1 - x0]
        return out

    def frame_slice(self) -> tuple[slice, slice]:
        """The crop's placement, for indexing a frame-sized array:
        `frame[rm.frame_slice()][rm.crop]` is the old `frame[rm.mask]`."""
        y0, x0 = self.origin
        h, w = self.crop.shape
        return (slice(y0, y0 + h), slice(x0, x0 + w))

    def union_from(self, other: "RegionMask") -> None:
        """In-place `self |= other`, growing the crop to cover both.

        Replaces `regions[best].mask[box] |= regions[i].mask[box]`.
        Absorption is the one place a RegionMask is mutated after
        construction and it has to stay in place: `resolve_small_regions`
        keeps index-parallel `areas`/`boxes` and re-reads the absorbing
        region through them.
        """
        sy0, sx0 = self.origin
        sh, sw = self.crop.shape
        oy0, ox0 = other.origin
        oh, ow = other.crop.shape
        ny0, nx0 = min(sy0, oy0), min(sx0, ox0)
        ny1, nx1 = max(sy0 + sh, oy0 + oh), max(sx0 + sw, ox0 + ow)
        if (ny0, nx0, ny1, nx1) == (sy0, sx0, sy0 + sh, sx0 + sw):
            grown = self.crop                      # already covers `other`
        else:
            grown = np.zeros((ny1 - ny0, nx1 - nx0), bool)
            grown[sy0 - ny0:sy0 - ny0 + sh, sx0 - nx0:sx0 - nx0 + sw] = self.crop
        grown[oy0 - ny0:oy0 - ny0 + oh, ox0 - nx0:ox0 - nx0 + ow] |= other.crop
        self.crop = grown
        self.origin = (ny0, nx0)


class Segmenter(ABC):
    """Produces per-region masks from the quantized layers."""

    name = "abstract"

    @abstractmethod
    def segment(self, quant: Quant, prep: Prep, cfg: PipelineConfig) -> list[RegionMask]:
        ...


class ClassicalSegmenter(Segmenter):
    name = "classical"

    def segment(self, quant: Quant, prep: Prep, cfg: PipelineConfig) -> list[RegionMask]:
        """One RegionMask per connected component, cropped at birth.

        `connectedComponentsWithStats` rather than `connectedComponents`
        because it hands back each component's bounding box for free, so the
        crop is a slice of the label image inside that box and no
        frame-sized temporary is ever built. Component order is unchanged
        (label 1..n-1 per layer, layers in order), which is what keeps the
        downstream small-region policy and every golden byte-identical.
        """
        out: list[RegionMask] = []
        frame_shape = tuple(quant.labels.shape)
        for layer in range(len(quant.thread_indices)):
            layer_mask = (quant.labels == layer).astype(np.uint8)
            if not layer_mask.any():
                continue
            n, cc, stats, _ = cv2.connectedComponentsWithStats(layer_mask, connectivity=8)
            for c in range(1, n):
                x0, y0, w, h = (int(v) for v in stats[c, :4])
                out.append(RegionMask(
                    crop=np.ascontiguousarray(cc[y0:y0 + h, x0:x0 + w] == c),
                    origin=(y0, x0), frame_shape=frame_shape,
                    layer=layer, source=self.name))
        return out


def _dilate(mask: np.ndarray) -> np.ndarray:
    return cv2.dilate(mask.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0


def _bbox(mask: np.ndarray) -> tuple[int, int, int, int] | None:
    """(y0, x0, y1, x1) with y1/x1 exclusive, or None for an empty mask."""
    rows = np.any(mask, axis=1)
    if not rows.any():
        return None
    cols = np.any(mask, axis=0)
    y0 = int(np.argmax(rows))
    y1 = int(len(rows) - np.argmax(rows[::-1]))
    x0 = int(np.argmax(cols))
    x1 = int(len(cols) - np.argmax(cols[::-1]))
    return (y0, x0, y1, x1)


# A small region is protected from absorption when at least this fraction of
# its own pixels overlap `Prep.enclosed_mask` — see `resolve_small_regions`'s
# docstring. Deliberately the same value as `stage4_vectorize.
# ENCLOSED_TAG_OVERLAP_THRESHOLD` (duplicated, not imported: importing
# `stage4_vectorize` here would be circular, since it already imports
# `RegionMask` from this module) and chosen on the same reasoning — a real
# match scores far above this on both fixtures that motivated it, so 0.6
# leaves headroom before a genuine enclosed hole would ever miss protection,
# while still refusing a small region that only grazes an enclosed patch
# along one edge.
ENCLOSED_PROTECT_OVERLAP = 0.6


def _chained_small_regions(regions, areas, boxes, small, min_area_px,
                           height, width) -> set[int]:
    """Sub-floor regions that form a connected structure clearing the floor.

    Returns the indices to KEEP as-is. Nothing is merged: the fragments of a
    banded ring alternate thread colours, so unioning them would invent a
    region that sews one colour over another. They are real content and each
    survives as its own region; stage 4 still re-tests every one against its
    own real-geometry floor, so nothing unsewable gets through here.

    Adjacency deliberately ignores the layer. Whether a sliver is part of a
    real structure is a question about geometry, not about which thread it
    ended up on — and in the motivating case the neighbours on either side of
    every arc are the OTHER colour, so a same-layer rule would see 84 isolated
    crumbs and chain nothing. Chains that still miss the floor together fall
    through to the per-region policy unchanged.
    """
    if len(small) < 2:
        return set()

    parent = {i: i for i in small}

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    # Adjacency by halo overlap, bbox-pruned exactly like the loop below.
    for pos, i in enumerate(small):
        bi = boxes[i]
        if bi is None:
            continue
        wy0, wx0 = max(0, bi[0] - 1), max(0, bi[1] - 1)
        wy1, wx1 = min(height, bi[2] + 1), min(width, bi[3] + 1)
        sub = regions[i].window(wy0, wx0, wy1, wx1)
        halo = _dilate(sub) & ~sub
        for j in small[pos + 1:]:
            bj = boxes[j]
            if bj is None or bj[2] <= wy0 or bj[0] >= wy1 or bj[3] <= wx0 or bj[1] >= wx1:
                continue
            if int((halo & regions[j].window(wy0, wx0, wy1, wx1)).sum()):
                ra, rb = find(i), find(j)
                if ra != rb:
                    parent[rb] = ra

    groups: dict[int, list[int]] = {}
    for i in small:
        groups.setdefault(find(i), []).append(i)

    chained: set[int] = set()
    for members in groups.values():
        if len(members) < 2:
            continue
        if sum(areas[m] for m in members) < min_area_px:
            continue  # still detail, even together
        chained.update(members)
    return chained


def resolve_small_regions(
    regions: list[RegionMask], cfg: PipelineConfig, px_per_mm: float,
    enclosed_mask: np.ndarray | None = None, *, chain_rescue: bool = True,
) -> tuple[list[RegionMask], list[dict]]:
    """Absorb or drop sub-sewable regions. Returns (kept, warnings).

    Every comparison here is windowed to the small region's own bounding box.
    A sliver's halo is a one-pixel ring a few dozen pixels around, and matching
    it against a neighbour used to AND two full megapixel masks together — on a
    real logo that was thousands of whole-image scans and about two thirds of
    the time stages 1-4 took. The arithmetic is unchanged: a halo is zero
    outside its own box, so cropping to that box cannot change a single count.

    `enclosed_mask` (`Prep.enclosed_mask`, optional — `None` reduces to the
    pre-existing behaviour byte-for-byte) is stage 1's raw, pre-quantization
    signal that a pixel is background-colored but NOT canvas-border-connected
    — a donut hole, a letter's counter. A small region built almost entirely
    from those pixels is not segmentation noise; it is exactly the real
    content `tag_enclosed_background` (stage 4, post-vectorization) exists to
    find and tag `enclosed_background` / unstitched-by-default, per `Prep.
    enclosed_mask`'s own docstring ("the pixels themselves become a real
    Region downstream"). Absorbing it into its enclosing neighbour here —
    which this function's ordinary small-region policy will otherwise always
    do, since an enclosed hole's only possible neighbour IS the shape that
    encloses it — erases that Region before stage 4 ever gets the chance,
    silently filling the hole in. Measured on the real benchmark fixture: the
    "A" in `testdata/photo/enthusiast_logo.png`'s wordmark has a genuine
    2.08 mm² triangular counter (`Prep.enclosed_mask` finds it correctly,
    comfortably above `cfg.min_detail_mm`'s sewable floor) that this exact
    path was silently absorbing into the "A" glyph's own ink region before
    this guard existed — confirmed by the final region's polygon carrying
    ZERO interior rings despite `stage4_vectorize.tag_enclosed_background`'s
    machinery being fully wired and working correctly for every OTHER
    enclosed feature in the corpus. A protected region skips absorption and
    drop entirely (added straight to the kept set); it still has to clear
    stage 4's own real-geometry floor to survive as a Region, same as any
    other mask this function keeps.
    """
    min_area_px = (cfg.min_detail_mm * px_per_mm) ** 2
    areas = [r.area for r in regions]
    small = [i for i, a in enumerate(areas) if a < min_area_px]
    if not small:
        return regions, []

    keep = [i for i, a in enumerate(areas) if a >= min_area_px]
    # `bbox` is the crop's own placement, so this no longer scans a frame
    # per region; an empty region keeps the None the old `_bbox` returned.
    boxes = [None if r.area == 0 else r.bbox for r in regions]
    height, width = regions[0].frame_shape
    report_floor_px = min_area_px * cfg.report_absorb_frac

    # A structure that arrives FRAGMENTED is not detail, however small its
    # pieces are individually. Quantization bands a gradient ring into arc
    # slivers; each sliver is sub-floor, and each sliver's best halo-share
    # neighbour is the large background region it sits on rather than the
    # neighbouring arc — so the ordinary policy below absorbs the entire ring
    # into the background one segment at a time. Measured 2026-08-17: an
    # 84-segment ring, 172 mm² and 40 mm across, digitised to ZERO sewn
    # regions with only an advisory ABSORBED_SMALL_SHAPES to show for it
    # (docs/shape-fidelity-findings-2026-08-17.md).
    #
    # So: test connected chains of small regions against the same floor FIRST.
    # A chain that clears it together is real content and every member is kept
    # as-is; the rest fall through to the per-region policy unchanged. No new
    # threshold — `min_area_px` is still the only bar, just applied to the
    # connected structure instead of to each crumb of it.
    # Gated on the SAME opt-out as the other rescue path below. This is a
    # rescue — it keeps geometry the floor would otherwise cull — so a caller
    # who set `small_shape_rescue=False` to get strict floor behaviour must
    # keep getting it. Missing this gate silently broke SAM2's
    # no-usable-regions fallback, which drives four sub-floor blobs with
    # rescue OFF and expects every one to drop.
    # `chain_rescue` is the LANE gate, separate from `cfg.small_shape_rescue`
    # (the user-facing opt-out). The photo segmenters pass False: measured
    # 2026-08-21 on `photo/summit_badge.png`, chaining there moves stage 2 from
    # 34 regions/12 threads to 46/15 and triples the palette's worst excess
    # (max_excess_de00 2.453 -> 7.763). Quantisation shatters a photo into
    # mutually-adjacent sub-floor fragments everywhere, which is exactly the
    # condition this rescue fires on, so it stops discriminating there. The
    # evidence this fix shipped on -- 15 pro-parity designs, 13 byte-identical
    # -- did not cover the photo lane. Re-open it behind a real measurement,
    # not by deleting this argument.
    chained = _chained_small_regions(
        regions, areas, boxes, small, min_area_px, height, width
    ) if (cfg.small_shape_rescue and chain_rescue) else set()
    if chained:
        small = [i for i in small if i not in chained]
    absorbed = dropped = 0
    absorbed_reportable = dropped_reportable = 0
    rescued: list[int] = []
    protected: list[int] = []

    # The run-tier floors, in mask units. The loop test uses 2*max(w, h) as a
    # perimeter proxy — a lower bound (the boundary must traverse the longer
    # extent twice), so a mask passing here definitely holds a sewable loop.
    # Stage 4 re-tests on the real polygon; this one only has to be cheap and
    # never rescue what geometry would then reject silently.
    noise_area_px = machine.RUN_MIN_AREA_MM2 * px_per_mm ** 2
    loop_floor_px = machine.RUN_MIN_LOOP_MM * px_per_mm

    # Deterministic order: smallest first, then by top-left position.
    def sort_key(i: int) -> tuple:
        box = boxes[i]
        return (areas[i], box[0], box[1]) if box else (areas[i], 0, 0)

    for i in sorted(small, key=sort_key):
        box = boxes[i]
        if box is None:
            dropped += 1
            continue
        if enclosed_mask is not None and areas[i] > 0:
            by0, bx0, by1, bx1 = box
            sub_mask = regions[i].window(by0, bx0, by1, bx1)
            sub_enclosed = enclosed_mask[by0:by1, bx0:bx1]
            if int((sub_mask & sub_enclosed).sum()) / areas[i] >= ENCLOSED_PROTECT_OVERLAP:
                protected.append(i)
                continue
        # The halo can only reach one pixel past the region, so this window
        # holds all of it; dilating the cropped mask inside the window gives
        # the same ring the full-image dilation would.
        wy0, wx0 = max(0, box[0] - 1), max(0, box[1] - 1)
        wy1, wx1 = min(height, box[2] + 1), min(width, box[3] + 1)
        sub = regions[i].window(wy0, wx0, wy1, wx1)
        halo = _dilate(sub) & ~sub

        best, best_share = None, 0
        for j in keep:
            jb = boxes[j]
            # No bbox overlap means no shared boundary; the share would be 0,
            # which never beat best_share anyway.
            if jb is None or jb[2] <= wy0 or jb[0] >= wy1 or jb[3] <= wx0 or jb[1] >= wx1:
                continue
            share = int((halo & regions[j].window(wy0, wx0, wy1, wx1)).sum())
            if share > best_share:
                best, best_share = j, share

        reportable = areas[i] >= report_floor_px
        if best is None:
            # No neighbour to absorb into: this is isolated artwork, and the
            # benchmark showed exactly what it tends to be — a logo's small
            # text, sitting alone on background. Keep it for the run tier
            # when it is at least the thread's own visual weight; below that
            # it is lint, and lint drops.
            box_h, box_w = box[2] - box[0], box[3] - box[1]
            if (cfg.small_shape_rescue and areas[i] >= noise_area_px
                    and 2 * max(box_h, box_w) >= loop_floor_px):
                rescued.append(i)
                continue
            dropped += 1
            dropped_reportable += int(reportable)
            continue
        regions[best].union_from(regions[i])
        # The absorbing region just grew; its box has to grow with it or a
        # later sliver could be rejected against a stale footprint.
        jb = boxes[best]
        boxes[best] = (min(jb[0], box[0]), min(jb[1], box[1]),
                       max(jb[2], box[2]), max(jb[3], box[3]))
        absorbed += 1
        absorbed_reportable += int(reportable)

    # Rescued and enclosed-protected masks ride along after the full-size
    # ones; stage 4 re-sorts its output, so their position here only has to
    # be deterministic (it is: both lists fill in the same smallest-first
    # order the loop walks).
    kept = ([regions[i] for i in keep] + [regions[i] for i in rescued]
            + [regions[i] for i in protected]
            + [regions[i] for i in sorted(chained)])
    warnings: list[dict] = []
    # Only regions big enough to have been intentional artwork are reported;
    # anti-alias slivers are cleaned up silently (see cfg.report_absorb_frac).
    if absorbed_reportable:
        warnings.append(
            warn(
                ABSORBED_SMALL_SHAPES,
                f"{absorbed_reportable} detail"
                f"{'s' if absorbed_reportable != 1 else ''} smaller than "
                f"{cfg.min_detail_mm} mm merged into the shape next to it.",
                count=absorbed_reportable,
                cleaned_total=absorbed,
            )
        )
    if dropped_reportable:
        warnings.append(
            warn(
                DROPPED_SMALL_SHAPES,
                f"{dropped_reportable} detail"
                f"{'s' if dropped_reportable != 1 else ''} smaller than "
                f"{cfg.min_detail_mm} mm could not be sewn and were removed.",
                count=dropped_reportable,
                cleaned_total=dropped,
            )
        )
    return kept, warnings


def compact_layers(regions, thread_indices: list[int]) -> tuple[list[int], list[dict]]:
    """Drop thread layers that ended up with no geometry.

    Runs AFTER vectorization, not after segmentation: a mask can still be
    dropped while being turned into a polygon, and a palette that lists a
    thread with nothing to sew would send the operator to the rack for a cone
    they never use. Accepts anything exposing an int layer via `.layer` (a
    RegionMask) or `.meta["layer"]` (a vectorized Region), and rewrites it to
    index the compacted list.
    """
    def get_layer(r) -> int:
        return r.meta["layer"] if hasattr(r, "meta") else r.layer

    def set_layer(r, v: int) -> None:
        if hasattr(r, "meta"):
            r.meta["layer"] = v
        else:
            r.layer = v

    used = sorted({get_layer(r) for r in regions})
    warnings: list[dict] = []
    if len(used) < len(thread_indices):
        warnings.append(
            warn(
                EMPTY_THREAD_LAYER,
                "A thread color ended up with nothing to sew and was removed from "
                "the color list.",
                count=len(thread_indices) - len(used),
            )
        )
    remap = {old: new for new, old in enumerate(used)}
    for r in regions:
        set_layer(r, remap[get_layer(r)])
    return [thread_indices[i] for i in used], warnings
