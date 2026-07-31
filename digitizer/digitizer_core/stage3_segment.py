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
    mask: np.ndarray     # (H, W) bool
    layer: int           # index into Quant.thread_indices
    source: str = "classical"


class Segmenter(ABC):
    """Produces per-region masks from the quantized layers."""

    name = "abstract"

    @abstractmethod
    def segment(self, quant: Quant, prep: Prep, cfg: PipelineConfig) -> list[RegionMask]:
        ...


class ClassicalSegmenter(Segmenter):
    name = "classical"

    def segment(self, quant: Quant, prep: Prep, cfg: PipelineConfig) -> list[RegionMask]:
        out: list[RegionMask] = []
        for layer in range(len(quant.thread_indices)):
            layer_mask = (quant.labels == layer).astype(np.uint8)
            if not layer_mask.any():
                continue
            n, cc = cv2.connectedComponents(layer_mask, connectivity=8)
            for c in range(1, n):
                out.append(RegionMask(mask=cc == c, layer=layer, source=self.name))
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


def resolve_small_regions(
    regions: list[RegionMask], cfg: PipelineConfig, px_per_mm: float
) -> tuple[list[RegionMask], list[dict]]:
    """Absorb or drop sub-sewable regions. Returns (kept, warnings).

    Every comparison here is windowed to the small region's own bounding box.
    A sliver's halo is a one-pixel ring a few dozen pixels around, and matching
    it against a neighbour used to AND two full megapixel masks together — on a
    real logo that was thousands of whole-image scans and about two thirds of
    the time stages 1-4 took. The arithmetic is unchanged: a halo is zero
    outside its own box, so cropping to that box cannot change a single count.
    """
    min_area_px = (cfg.min_detail_mm * px_per_mm) ** 2
    areas = [int(r.mask.sum()) for r in regions]
    small = [i for i, a in enumerate(areas) if a < min_area_px]
    if not small:
        return regions, []

    keep = [i for i, a in enumerate(areas) if a >= min_area_px]
    boxes = [_bbox(r.mask) for r in regions]
    height, width = regions[0].mask.shape
    report_floor_px = min_area_px * cfg.report_absorb_frac
    absorbed = dropped = 0
    absorbed_reportable = dropped_reportable = 0
    rescued: list[int] = []

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
        # The halo can only reach one pixel past the region, so this window
        # holds all of it; dilating the cropped mask inside the window gives
        # the same ring the full-image dilation would.
        wy0, wx0 = max(0, box[0] - 1), max(0, box[1] - 1)
        wy1, wx1 = min(height, box[2] + 1), min(width, box[3] + 1)
        sub = regions[i].mask[wy0:wy1, wx0:wx1]
        halo = _dilate(sub) & ~sub

        best, best_share = None, 0
        for j in keep:
            jb = boxes[j]
            # No bbox overlap means no shared boundary; the share would be 0,
            # which never beat best_share anyway.
            if jb is None or jb[2] <= wy0 or jb[0] >= wy1 or jb[3] <= wx0 or jb[1] >= wx1:
                continue
            share = int((halo & regions[j].mask[wy0:wy1, wx0:wx1]).sum())
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
        regions[best].mask[box[0]:box[2], box[1]:box[3]] |= \
            regions[i].mask[box[0]:box[2], box[1]:box[3]]
        # The absorbing region just grew; its box has to grow with it or a
        # later sliver could be rejected against a stale footprint.
        jb = boxes[best]
        boxes[best] = (min(jb[0], box[0]), min(jb[1], box[1]),
                       max(jb[2], box[2]), max(jb[3], box[3]))
        absorbed += 1
        absorbed_reportable += int(reportable)

    # Rescued masks ride along after the full-size ones; stage 4 re-sorts its
    # output, so their position here only has to be deterministic (it is:
    # `rescued` fills in the same smallest-first order the loop walks).
    kept = [regions[i] for i in keep] + [regions[i] for i in rescued]
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
