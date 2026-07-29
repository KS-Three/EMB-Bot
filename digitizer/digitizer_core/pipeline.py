"""Stage orchestration — the one entry point callers use.

`run_stages` is stages 1-4 only (blueprint build step 1). Stitch planning,
the stitch processor, and export arrive in later steps and will consume
PipelineResult without changing it: the regions, palette, and px_per_mm here
are exactly what stage 5 (overlap resolution) needs to begin.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from shapely.geometry import Polygon

from . import debugviz
from .config import PipelineConfig
from .regions import Region
from .stage1_prep import Prep, prep
from .stage2_quantize import Quant, quantize
from .stage3_segment import (
    ClassicalSegmenter,
    Segmenter,
    compact_layers,
    resolve_small_regions,
)
from .stage4_vectorize import vectorize
from .threads import CHART
from .warnings_codes import DROPPED_SMALL_SHAPES, warn


@dataclass
class BackgroundInfo:
    detected: bool
    outline_mm: list[list[float]] | None = None
    stitched: bool = False


@dataclass
class PipelineResult:
    regions: list[Region]
    palette: list[dict]              # sew-order thread list
    background: BackgroundInfo
    px_per_mm: float
    design_size_mm: tuple[float, float]
    warnings: list[dict] = field(default_factory=list)
    segmenter: str = "classical"
    debug_dir: Path | None = None

    @property
    def shape_ids(self) -> list[str]:
        return [r.shape_id for r in self.regions]


def run_stages(
    image: str | Path | bytes | np.ndarray,
    cfg: PipelineConfig | None = None,
    segmenter: Segmenter | None = None,
) -> PipelineResult:
    cfg = cfg or PipelineConfig()
    seg = segmenter or ClassicalSegmenter()
    dbg = Path(cfg.debug_dir) if cfg.debug_dir else None

    p: Prep = prep(image, cfg)
    if dbg:
        debugviz.stage1(dbg, p.rgb, p.bg_mask)

    q: Quant = quantize(p, cfg)
    if dbg:
        debugviz.stage2(dbg, q.labels, q.thread_indices)

    masks = seg.segment(q, p, cfg)
    masks, small_warnings = resolve_small_regions(masks, cfg, p.px_per_mm)
    if dbg:
        debugviz.stage3(dbg, p.rgb, masks)

    # Vectorize against the FULL quant palette, then compact — a mask can be
    # dropped during simplification, so the palette can only be finalized
    # once the surviving geometry is known.
    regions: list[Region]
    regions, dropped_areas = vectorize(masks, q.thread_indices, p, cfg)
    thread_indices, layer_warnings = compact_layers(regions, q.thread_indices)

    vec_warnings: list[dict] = []
    if dropped_areas:
        floor = (cfg.min_detail_mm ** 2) * cfg.report_absorb_frac
        reportable = sum(1 for a in dropped_areas if a >= floor)
        if reportable:
            vec_warnings.append(
                warn(
                    DROPPED_SMALL_SHAPES,
                    f"{reportable} detail{'s' if reportable != 1 else ''} were too "
                    "small or thin to hold a stitch and were removed.",
                    count=reportable,
                    cleaned_total=len(dropped_areas),
                )
            )
    if dbg:
        debugviz.stage4(dbg, p.rgb, regions, p.px_per_mm, p.art_bbox)

    x0, y0, x1, y1 = p.art_bbox
    design = ((x1 - x0) / p.px_per_mm, (y1 - y0) / p.px_per_mm)

    bg_outline_mm = None
    if p.bg_outline_px is not None and len(p.bg_outline_px) >= 3:
        cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
        pts = p.bg_outline_px.astype(np.float64)
        ring = np.column_stack(
            [(pts[:, 0] - cx) / p.px_per_mm, (pts[:, 1] - cy) / p.px_per_mm]
        )
        # Simplify with the same tolerance the region polygons use.
        simple = Polygon(ring).simplify(cfg.simplify_tol_mm, preserve_topology=True)
        if not simple.is_empty and simple.geom_type == "Polygon":
            bg_outline_mm = [[round(x, 3), round(y, 3)] for x, y in simple.exterior.coords]

    # Stage 3 and stage 4 can both drop shapes, and the review screen should
    # see ONE "n details removed" line, not one per pipeline stage.
    def merge_warnings(items: list[dict]) -> list[dict]:
        out: list[dict] = []
        by_code: dict[str, dict] = {}
        for w in items:
            prev = by_code.get(w["code"])
            if prev is None:
                copy = dict(w)
                by_code[w["code"]] = copy
                out.append(copy)
                continue
            for key in ("count", "cleaned_total", "intruded_px", "dropped"):
                if key in w:
                    prev[key] = prev.get(key, 0) + w[key]
            if "count" in prev:
                noun = "detail" if prev["count"] == 1 else "details"
                prev["message"] = (
                    f"{prev['count']} {noun} smaller than {cfg.min_detail_mm} mm "
                    "could not be sewn and were removed."
                    if w["code"] == DROPPED_SMALL_SHAPES
                    else prev["message"]
                )
        return out

    palette = [
        {
            "brand": "Isacord",
            "number": CHART[t].number,
            "name": CHART[t].name,
            "rgb": list(CHART[t].rgb),
        }
        for t in thread_indices
    ]

    return PipelineResult(
        regions=regions,
        palette=palette,
        background=BackgroundInfo(
            detected=bool(p.bg_mask.any()),
            outline_mm=bg_outline_mm,
            stitched=False,
        ),
        px_per_mm=p.px_per_mm,
        design_size_mm=design,
        warnings=merge_warnings(
            [*p.warnings, *q.warnings, *small_warnings, *vec_warnings, *layer_warnings]
        ),
        segmenter=seg.name,
        debug_dir=dbg,
    )
