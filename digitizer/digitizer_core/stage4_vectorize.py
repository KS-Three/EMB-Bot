"""Stage 4 — masks to simplified mm-space polygons with holes.

Output coordinate system is the JSON contract's, pinned here so nothing
downstream has to guess:
    millimetres, floats, origin at the ARTWORK bbox center, **y-axis DOWN**.
Image space is already y-down, so no flip happens here. EMB-Bot's own engine
is +y UP, which makes the browser boundary the one place a mirror can creep
in — that conversion belongs to the integration adapter (step 10) and has a
golden test of its own.

Each RegionMask is a single connected component, so its contour hierarchy is
exactly one outer shell plus its holes (a same-color island inside a hole is
not connected to the shell, so it arrives as its own RegionMask). RETR_CCOMP
is therefore sufficient; nested-shell handling is not needed at this depth.
"""
from __future__ import annotations

import cv2
import numpy as np
from shapely.geometry import Polygon
from shapely.validation import make_valid

from .config import PipelineConfig
from .regions import Region, assign_shape_ids
from .stage1_prep import Prep
from .stage3_segment import RegionMask
from .threads import CHART


def _to_mm(pts: np.ndarray, cx: float, cy: float, px_per_mm: float) -> np.ndarray:
    out = pts.astype(np.float64)
    out[:, 0] = (out[:, 0] - cx) / px_per_mm
    out[:, 1] = (out[:, 1] - cy) / px_per_mm
    return out


def vectorize(
    region_masks: list[RegionMask],
    thread_indices: list[int],
    p: Prep,
    cfg: PipelineConfig,
) -> tuple[list[Region], list[float]]:
    """-> (regions, dropped_areas_mm2).

    A mask can still vanish here: simplification collapses a sliver below
    three points or below a sewable area. Those drops are RETURNED, never
    swallowed — the pipeline folds them into the same warning stage 3 uses,
    because a shape disappearing with no trace is the failure mode that
    makes an auto-digitizer untrustworthy.
    """
    x0, y0, x1, y1 = p.art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    eps_px = max(0.5, cfg.simplify_tol_mm * p.px_per_mm)
    min_area_mm2 = (cfg.min_detail_mm ** 2) * 0.25  # a sliver after simplification

    regions: list[Region] = []
    dropped: list[float] = []

    def note_drop(rm: RegionMask) -> None:
        dropped.append(float(rm.mask.sum()) / (p.px_per_mm ** 2))

    for rm in region_masks:
        contours, hierarchy = cv2.findContours(
            rm.mask.astype(np.uint8), cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE
        )
        if not contours or hierarchy is None:
            note_drop(rm)
            continue
        hier = hierarchy[0]

        # Outer contours have no parent; each may own holes as children.
        outers = [i for i in range(len(contours)) if hier[i][3] == -1]
        if not outers:
            note_drop(rm)
            continue
        # A single connected component yields one meaningful shell; if
        # simplification splintered it, keep the largest.
        outer = max(outers, key=lambda i: cv2.contourArea(contours[i]))

        shell_px = cv2.approxPolyDP(contours[outer], eps_px, True).reshape(-1, 2)
        if len(shell_px) < 3:
            note_drop(rm)
            continue
        shell = _to_mm(shell_px, cx, cy, p.px_per_mm)

        holes = []
        for i in range(len(contours)):
            if hier[i][3] != outer:
                continue
            h_px = cv2.approxPolyDP(contours[i], eps_px, True).reshape(-1, 2)
            if len(h_px) < 3:
                continue
            ring = _to_mm(h_px, cx, cy, p.px_per_mm)
            if Polygon(ring).area >= min_area_mm2:
                holes.append(ring)

        poly = Polygon(shell, holes)
        if not poly.is_valid:
            fixed = make_valid(poly)
            # make_valid can return a collection; take the largest polygon part.
            if fixed.geom_type == "Polygon":
                poly = fixed
            elif hasattr(fixed, "geoms"):
                polys = [g for g in fixed.geoms if g.geom_type == "Polygon"]
                if not polys:
                    note_drop(rm)
                    continue
                poly = max(polys, key=lambda g: g.area)
            else:
                note_drop(rm)
                continue
        if poly.is_empty or poly.area < min_area_mm2:
            note_drop(rm)
            continue

        thread = CHART[thread_indices[rm.layer]]
        regions.append(
            Region(
                shape_id="",
                polygon=poly,
                thread_index=thread_indices[rm.layer],
                thread_number=thread.number,
                area_mm2=float(poly.area),
                source=rm.source,
                meta={"layer": rm.layer},
            )
        )

    assign_shape_ids(regions)
    # Stable output order: largest first within a layer, layers in sew order.
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))
    return regions, dropped
