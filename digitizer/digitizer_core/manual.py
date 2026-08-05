"""Manual digitizing — a user-authored shape list in, a `PipelineResult` out,
skipping stages 1-4 entirely.

Auto-digitize answers "what shapes are in this artwork, in what threads"
(stages 1-4, `run_stages`) before stages 5-7 (`plan_stitches`) turn that into
stitches. A manually-authored design already answers the first question by
construction — the caller drew the shapes and picked the threads — so
`build_manual_result` is a second, narrower way to reach the exact same
`PipelineResult` contract `plan_stitches` already consumes, with no image, no
background removal, no quantization, no segmentation.

**Coordinate contract**, inherited unchanged from `stitches.py`/
`stage4_vectorize.py`: millimetres, floats, y-axis DOWN. Every shape's
`polygon` is taken as literal physical millimetres, not design units to be
scaled — `PipelineConfig.target_width_mm` is therefore a no-op here (it only
ever meant "the px->mm factor for THIS artwork", and there are no pixels).
The combined bounding box of every shape is recentred to the origin, matching
the "origin at the artwork bbox center" convention `run_stages` produces, so a
manual design lands in the same coordinate space every downstream consumer
(`plan_stitches`, `adapter.py`) already assumes and overlays sanely with any
review-screen tooling built against that convention.

**Sew order.** Shapes sharing a resolved thread snap into one color layer/
block, largest combined area first — the same "big fields go down first"
default rule stage 2 already encodes for auto-digitize (see
`stage5_overlap.py`'s module docstring). There is no per-shape `layer`/
`sew_order` input in this first cut; shapes needing an explicit within-color
order can get there later the same way an auto-digitize review edit does
(`Region.meta["sew_order"]`), a clean follow-up rather than a gap that blocks
this one.

**Stitch technique.** Each shape names its tier directly — "satin" | "fill" |
"run" — written straight to `Region.meta["tier"]`, the same field the
review-screen `shape_overrides[...].tier` override already writes (see
`regions.apply_shape_edits`). There is no "auto" here: a manual shape is a
deliberate choice, not artwork for the ribbon-width classifier to guess at.
A tier stage 6 cannot actually sew (e.g. "satin" on a skeleton the module
cannot resolve) falls through the exact same rescue ladder an auto-digitize
forced tier does — nothing here weakens that contract.
"""
from __future__ import annotations

import numpy as np
from shapely.affinity import translate
from shapely.geometry import Polygon
from shapely.validation import explain_validity

from .config import PipelineConfig
from .pipeline import BackgroundInfo, PipelineResult
from .regions import Region, assign_shape_ids
from .threads import Chart, chart_for, rgb_to_lab

# The tiers a manual shape may request. Deliberately narrower than
# `regions._TIER_VALUES` ({"auto", "satin", "fill", "run", "sketch"}): "auto"
# has nothing to classify from but the polygon (fine for artwork, an odd
# default for a shape someone drew on purpose), and "sketch" needs source
# pixels manual digitizing never has.
VALID_TECHNIQUES = frozenset({"satin", "fill", "run"})


def _validate_ring(points, *, label: str) -> list[tuple[float, float]]:
    if not isinstance(points, (list, tuple)) or len(points) < 3:
        raise ValueError(f"{label} must be a list of at least 3 [x, y] points")
    out: list[tuple[float, float]] = []
    for i, pt in enumerate(points):
        if (not isinstance(pt, (list, tuple)) or len(pt) != 2
                or isinstance(pt, (str, bytes))):
            raise ValueError(f"{label}[{i}] must be an [x, y] pair")
        x, y = pt
        if (not isinstance(x, (int, float)) or isinstance(x, bool)
                or not isinstance(y, (int, float)) or isinstance(y, bool)):
            raise ValueError(f"{label}[{i}] coordinates must be numbers")
        xf, yf = float(x), float(y)
        if not (np.isfinite(xf) and np.isfinite(yf)):
            raise ValueError(f"{label}[{i}] coordinates must be finite")
        out.append((xf, yf))
    return out


def _build_polygon(shape: dict, index: int) -> Polygon:
    if not isinstance(shape.get("polygon"), (list, tuple)):
        raise ValueError(f"shapes[{index}] is missing a 'polygon' (list of [x, y] mm points)")
    exterior = _validate_ring(shape["polygon"], label=f"shapes[{index}].polygon")

    holes_raw = shape.get("holes") or []
    if not isinstance(holes_raw, (list, tuple)):
        raise ValueError(f"shapes[{index}].holes must be a list of rings")
    holes = [_validate_ring(h, label=f"shapes[{index}].holes[{j}]")
             for j, h in enumerate(holes_raw)]

    try:
        poly = Polygon(exterior, holes)
    except Exception as exc:  # shapely raises assorted errors on bad rings
        raise ValueError(f"shapes[{index}].polygon is not a usable polygon: {exc}") from exc

    # Validity first: a self-intersecting bowtie's shoelace area can cancel to
    # (near) zero before `is_valid` is even consulted, and "self-intersecting"
    # is the more useful diagnosis than "degenerate" for that shape.
    if not poly.is_valid:
        raise ValueError(
            f"shapes[{index}].polygon is self-intersecting or otherwise invalid "
            f"({explain_validity(poly)})"
        )
    if poly.is_empty or poly.area <= 0:
        raise ValueError(
            f"shapes[{index}].polygon is degenerate (zero area) — check for "
            "collinear or duplicate points"
        )
    return poly


def _resolve_thread(shape: dict, index: int, chart: Chart) -> tuple[int, str]:
    has_index = shape.get("thread_index") is not None
    has_rgb = shape.get("thread_rgb") is not None
    if has_index and has_rgb:
        raise ValueError(
            f"shapes[{index}] must set only one of thread_index / thread_rgb, not both"
        )
    if has_index:
        t = shape["thread_index"]
        if not isinstance(t, int) or isinstance(t, bool) or not 0 <= t < len(chart):
            raise ValueError(
                f"shapes[{index}].thread_index must be an integer 0..{len(chart) - 1}"
            )
        return t, chart[t].number
    if has_rgb:
        rgb = shape["thread_rgb"]
        if (not isinstance(rgb, (list, tuple)) or len(rgb) != 3
                or not all(isinstance(c, (int, float)) and not isinstance(c, bool)
                           for c in rgb)
                or not all(0 <= c <= 255 for c in rgb)):
            raise ValueError(
                f"shapes[{index}].thread_rgb must be [r, g, b], each 0..255"
            )
        lab = rgb_to_lab(np.array([[float(c) for c in rgb]]))[0]
        t = chart.nearest_index(lab)
        return t, chart[t].number
    raise ValueError(
        f"shapes[{index}] must set thread_index (int) or thread_rgb ([r, g, b])"
    )


def _resolve_technique(shape: dict, index: int) -> str:
    technique = shape.get("technique")
    if technique is None:
        raise ValueError(
            f"shapes[{index}] is missing 'technique' "
            f"(one of {sorted(VALID_TECHNIQUES)})"
        )
    if not isinstance(technique, str) or technique.lower() not in VALID_TECHNIQUES:
        raise ValueError(
            f"shapes[{index}].technique {technique!r} must be one of "
            f"{sorted(VALID_TECHNIQUES)}"
        )
    return technique.lower()


def _resolve_fill_angle(shape: dict, index: int) -> float | None:
    angle = shape.get("fill_angle_deg")
    if angle is None:
        return None
    if not isinstance(angle, (int, float)) or isinstance(angle, bool):
        raise ValueError(f"shapes[{index}].fill_angle_deg must be a number")
    angle = float(angle)
    if not np.isfinite(angle):
        raise ValueError(f"shapes[{index}].fill_angle_deg must be finite")
    return angle


def build_manual_result(shapes: list[dict], cfg: PipelineConfig | None = None) -> PipelineResult:
    """Hand-authored shapes -> a `PipelineResult` `plan_stitches` can consume
    unchanged. Raises `ValueError` (never crashes) on anything invalid: an
    empty list, a malformed shape, a self-intersecting or degenerate polygon,
    a bad thread selection, an unsupported technique.

    Each item of `shapes` is a dict:
        polygon: [[x, y], ...]         required, mm, >= 3 points
        holes: [[[x, y], ...], ...]    optional interior rings, mm
        technique: "satin" | "fill" | "run"   required
        thread_index: int              one of thread_index / thread_rgb,
        thread_rgb: [r, g, b]          required (index into cfg's chart, or
                                        an RGB triple snapped to the nearest
                                        chart thread by CIEDE2000)
        fill_angle_deg: float          optional, per-shape fill angle
                                        (mirrors the review-screen override)
    """
    cfg = cfg or PipelineConfig()
    if not isinstance(shapes, (list, tuple)):
        raise ValueError("shapes must be a list of shape objects")
    if not shapes:
        raise ValueError("shapes must be a non-empty list — nothing to digitize")

    chart = chart_for(cfg)

    parsed: list[dict] = []
    for i, shape in enumerate(shapes):
        if not isinstance(shape, dict):
            raise ValueError(f"shapes[{i}] must be an object")
        poly = _build_polygon(shape, i)
        thread_index, thread_number = _resolve_thread(shape, i, chart)
        technique = _resolve_technique(shape, i)
        fill_angle = _resolve_fill_angle(shape, i)
        parsed.append({
            "polygon": poly,
            "thread_index": thread_index,
            "thread_number": thread_number,
            "technique": technique,
            "fill_angle_deg": fill_angle,
        })

    # Recentre on the combined bbox, matching "origin at the artwork bbox
    # center" (stitches.py) — the coordinate space plan_stitches, adapter.py
    # and every review-screen consumer already assume regions arrive in.
    bounds = [p["polygon"].bounds for p in parsed]
    x0 = min(b[0] for b in bounds)
    y0 = min(b[1] for b in bounds)
    x1 = max(b[2] for b in bounds)
    y1 = max(b[3] for b in bounds)
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    if cx != 0.0 or cy != 0.0:
        for p in parsed:
            p["polygon"] = translate(p["polygon"], xoff=-cx, yoff=-cy)

    # Sew order: shapes of one resolved thread share a color layer/block,
    # largest combined area first (stage5_overlap.py's own "big fields down
    # first" rule for auto-digitize) — dense 0..n-1, exactly what
    # resolve_overlaps/sequence already assume of meta["layer"].
    by_thread: dict[int, list[dict]] = {}
    for p in parsed:
        by_thread.setdefault(p["thread_index"], []).append(p)
    layer_order = sorted(
        by_thread, key=lambda t: -sum(p["polygon"].area for p in by_thread[t])
    )
    layer_of = {t: i for i, t in enumerate(layer_order)}

    regions: list[Region] = []
    for p in parsed:
        meta: dict = {"layer": layer_of[p["thread_index"]], "tier": p["technique"]}
        if p["fill_angle_deg"] is not None:
            meta["fill_angle_deg"] = p["fill_angle_deg"]
        regions.append(
            Region(
                shape_id="",
                polygon=p["polygon"],
                thread_index=p["thread_index"],
                thread_number=p["thread_number"],
                area_mm2=float(p["polygon"].area),
                source="manual",
                meta=meta,
            )
        )
    assign_shape_ids(regions)
    # Stable output order: largest first within a layer, layers in sew order —
    # the same order stage 4 promises (stage4_vectorize.vectorize's own tail).
    regions.sort(key=lambda r: (r.meta["layer"], -r.area_mm2, r.shape_id))

    palette = [
        {
            "brand": chart.label,
            "brand_id": chart.id,
            "number": chart[t].number,
            "name": chart[t].name,
            "rgb": list(chart[t].rgb),
        }
        for t in layer_order
    ]

    return PipelineResult(
        regions=regions,
        palette=palette,
        background=BackgroundInfo(detected=False, outline_mm=None, stitched=False),
        # No raster ever backed this generation, so there is no real px->mm
        # factor to report; None is the honest answer (vs. inventing one that
        # invites a client to convert against it).
        px_per_mm=None,
        design_size_mm=(x1 - x0, y1 - y0),
        warnings=[],
        segmenter="manual",
        debug_dir=None,
        source_pixels=None,
        design_class="flat",
    )
