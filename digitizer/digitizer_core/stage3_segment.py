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
boundary with it, or DROPPED when it has no neighbor. Both are counted and
warned — silently deleting art is the failure mode that erodes trust.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

import cv2
import numpy as np

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


def resolve_small_regions(
    regions: list[RegionMask], cfg: PipelineConfig, px_per_mm: float
) -> tuple[list[RegionMask], list[dict]]:
    """Absorb or drop sub-sewable regions. Returns (kept, warnings)."""
    min_area_px = (cfg.min_detail_mm * px_per_mm) ** 2
    areas = [int(r.mask.sum()) for r in regions]
    small = [i for i, a in enumerate(areas) if a < min_area_px]
    if not small:
        return regions, []

    keep = [i for i, a in enumerate(areas) if a >= min_area_px]
    report_floor_px = min_area_px * cfg.report_absorb_frac
    absorbed = dropped = 0
    absorbed_reportable = dropped_reportable = 0
    # Deterministic order: smallest first, then by top-left position.
    def sort_key(i: int) -> tuple:
        ys, xs = np.nonzero(regions[i].mask)
        return (areas[i], int(ys.min()), int(xs.min()))

    for i in sorted(small, key=sort_key):
        halo = _dilate(regions[i].mask) & ~regions[i].mask
        best, best_share = None, 0
        for j in keep:
            share = int((halo & regions[j].mask).sum())
            if share > best_share:
                best, best_share = j, share
        reportable = areas[i] >= report_floor_px
        if best is None:
            dropped += 1
            dropped_reportable += int(reportable)
            continue
        regions[best].mask = regions[best].mask | regions[i].mask
        absorbed += 1
        absorbed_reportable += int(reportable)

    kept = [regions[i] for i in keep]
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
