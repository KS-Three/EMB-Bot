"""Per-stage debug PNGs — the visual record for reviewing pipeline behavior.

Written only when cfg.debug_dir is set (never in the service's hot path).
Filenames are stage-prefixed so the directory reads in pipeline order.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .threads import CHART, Chart


def _chart(chart: Chart | None) -> Chart:
    """Debug renders take the chart as an optional argument: callers that have
    a config pass its brand, and ad-hoc calls from a REPL get the default."""
    return chart if chart is not None else CHART


def _write(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR))


def stage1(dir_: Path, rgb: np.ndarray, bg_mask: np.ndarray) -> None:
    _write(dir_ / "stage1_denoised.png", rgb)
    over = rgb.copy()
    over[bg_mask] = (over[bg_mask] * 0.25 + np.array([255, 0, 255]) * 0.75).astype(np.uint8)
    _write(dir_ / "stage1_bg.png", over)


def stage1_photo_prep(dir_: Path, rgb_tone: np.ndarray, rgb_prepped: np.ndarray) -> None:
    """Photo prep (stage1_photo_prep): the tone-rescued raster and the final
    texture-killed one the region former will actually see."""
    _write(dir_ / "stage1_photo_tone.png", rgb_tone)
    _write(dir_ / "stage1_photo_prepped.png", rgb_prepped)


def stage2(dir_: Path, labels: np.ndarray, thread_indices: list[int],
           chart: Chart | None = None) -> None:
    rng = np.random.default_rng(7)
    palette = rng.integers(40, 235, size=(max(1, labels.max() + 1), 3))
    viz = np.zeros(labels.shape + (3,), np.uint8)
    for j in range(labels.max() + 1):
        viz[labels == j] = palette[j]
    _write(dir_ / "stage2_labels.png", viz)

    ch = _chart(chart)
    snapped = np.full(labels.shape + (3,), 255, np.uint8)
    for j, t in enumerate(thread_indices):
        snapped[labels == j] = ch[t].rgb
    _write(dir_ / "stage2_snapped.png", snapped)


def stage3(dir_: Path, rgb: np.ndarray, region_masks) -> None:
    viz = (rgb * 0.35 + 255 * 0.65).astype(np.uint8)
    rng = np.random.default_rng(11)
    for rm in region_masks:
        color = tuple(int(v) for v in rng.integers(0, 200, 3))
        cnts, _ = cv2.findContours(
            rm.mask.astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(viz, cnts, -1, color, 2)
    _write(dir_ / "stage3_regions.png", viz)


def stage4(dir_: Path, rgb: np.ndarray, regions, px_per_mm: float, art_bbox,
           chart: Chart | None = None) -> None:
    ch = _chart(chart)
    x0, y0, x1, y1 = art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    viz = (rgb * 0.3 + 255 * 0.7).astype(np.uint8)

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        a[:, 0] = a[:, 0] * px_per_mm + cx
        a[:, 1] = a[:, 1] * px_per_mm + cy
        return a.astype(np.int32)

    for r in regions:
        thread_rgb = tuple(int(v) for v in ch[r.thread_index].rgb)
        cv2.polylines(viz, [to_px(r.polygon.exterior.coords)], True, thread_rgb, 2)
        for hole in r.polygon.interiors:
            cv2.polylines(viz, [to_px(hole.coords)], True, (255, 0, 255), 2)
        c = r.polygon.centroid
        cv2.putText(
            viz,
            r.shape_id,
            (int(c.x * px_per_mm + cx) - 30, int(c.y * px_per_mm + cy)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            (20, 20, 20),
            1,
            cv2.LINE_AA,
        )
    _write(dir_ / "stage4_vectors.png", viz)


# --- Stitch-level renders (build step 3) ----------------------------------
#
# These are drawn in mm space at a fixed scale rather than over the source
# image: what matters now is the stitch path itself, and at source resolution
# a 0.4 mm row spacing collapses into a solid block where nothing is judgable.

_MM_SCALE = 12          # px per mm in stitch renders
_MM_MARGIN = 6          # mm of empty space around the design


def _mm_canvas(size_mm, scale: int = _MM_SCALE):
    w_mm, h_mm = size_mm
    w = int((w_mm + 2 * _MM_MARGIN) * scale)
    h = int((h_mm + 2 * _MM_MARGIN) * scale)
    img = np.full((max(h, 1), max(w, 1), 3), 250, np.uint8)

    def to_px(x_mm: float, y_mm: float) -> tuple[int, int]:
        return (int(round((x_mm + w_mm / 2 + _MM_MARGIN) * scale)),
                int(round((y_mm + h_mm / 2 + _MM_MARGIN) * scale)))

    return img, to_px


def stage5(dir_: Path, planned, size_mm, chart: Chart | None = None) -> None:
    """Sewing geometry after underlap and pull compensation, in sew order."""
    ch = _chart(chart)
    viz, to_px = _mm_canvas(size_mm)
    for p in planned:
        color = tuple(int(v) for v in ch[p.region.thread_index].rgb)
        pts = np.array([to_px(x, y) for x, y in p.polygon.exterior.coords], np.int32)
        cv2.fillPoly(viz, [pts], color)
        for hole in p.polygon.interiors:
            hp = np.array([to_px(x, y) for x, y in hole.coords], np.int32)
            cv2.fillPoly(viz, [hp], (250, 250, 250))
    for i, p in enumerate(planned):
        c = p.polygon.centroid
        cv2.putText(viz, str(i), to_px(c.x, c.y), cv2.FONT_HERSHEY_SIMPLEX,
                    0.5, (10, 10, 10), 2, cv2.LINE_AA)
    _write(dir_ / "stage5_sewgeometry.png", viz)


def stage6(dir_: Path, plan, size_mm) -> None:
    """Every stitch, in thread color: fill and underlay solid, travel dashed,
    needle-up moves in magenta, needle penetrations dotted on the second image.
    """
    viz, to_px = _mm_canvas(size_mm)
    dots, _ = _mm_canvas(size_mm)
    prev = None
    for block, run in plan.iter_runs():
        color = tuple(int(v) for v in block.rgb)
        if run.jump and prev is not None:
            cv2.line(viz, to_px(*prev), to_px(*run.points[0]),
                     (255, 0, 255) if run.trim else (120, 120, 255), 1, cv2.LINE_AA)
        light = tuple(min(255, int(c * 0.4 + 255 * 0.6)) for c in color)
        draw = light if run.kind == "underlay" else color
        thickness = 1 if run.kind in ("underlay", "travel") else 2
        for a, b in zip(run.points, run.points[1:]):
            cv2.line(viz, to_px(*a), to_px(*b), draw, thickness, cv2.LINE_AA)
        for x, y in run.points:
            cv2.circle(dots, to_px(x, y), 1, color, -1)
        prev = run.points[-1]
    _write(dir_ / "stage6_stitches.png", viz)
    _write(dir_ / "stage6_penetrations.png", dots)


# --- Gradient blend fill (stage6_blend.py) ---------------------------------
#
# Its own pair, distinct from stage6() above: a blend group is several
# interleaved fill layers sharing one shape, and neither the merged stitch
# render nor the penetration dots make a phase-offset or shade-decomposition
# bug visible. These do.

_SWATCH_PX = 60


def stage6_blend_shades(dir_: Path, shade_rgbs: list[tuple[int, int, int]]) -> None:
    """A strip of the N decomposed shades, in ramp order — the review record
    for whether the chart-snap picked colors that actually step from light
    to dark instead of, say, all landing on the same cone."""
    n = max(1, len(shade_rgbs))
    img = np.full((_SWATCH_PX, _SWATCH_PX * n, 3), 250, np.uint8)
    for i, rgb in enumerate(shade_rgbs):
        img[:, i * _SWATCH_PX:(i + 1) * _SWATCH_PX] = rgb
    _write(dir_ / "stage6_blend_shades.png", img)


# --- Photo segmentation (stage2_photo_segment.py) ---------------------------
#
# Three artifacts, each answering a different question a plain stage2()
# render can't: did SLIC's raw oversegmentation look reasonable at all, did
# the hierarchical merge actually consolidate it (the boundary overlay is
# the point — a merge that did nothing still LOOKS like SLIC without one),
# and what did the region-count/area numbers actually land on.


def stage2_photo_slic(dir_: Path, rgb: np.ndarray, slic_labels: np.ndarray) -> None:
    """Raw SLIC superpixel boundaries over the source image — the BEFORE
    picture for stage2_photo_merged, so an empty-looking merge is obviously
    a no-op rather than a guess."""
    from skimage.segmentation import mark_boundaries

    viz = mark_boundaries(rgb, slic_labels, color=(1, 0, 1), mode="thick")
    _write(dir_ / "stage2_photo_slic.png", (viz * 255).round())


def stage2_photo_merged(
    dir_: Path, rgb: np.ndarray, labels: np.ndarray, mean_rgb: dict[int, tuple]
) -> None:
    """Final merged region boundaries, filled with each region's own mean
    color — the one that shows whether merging actually worked: a real
    consolidation shows a handful of flat-filled blobs, a no-op still shows
    SLIC's raw grid tinted per-superpixel."""
    from skimage.segmentation import mark_boundaries

    fill = rgb.copy()
    for lbl, region_rgb in mean_rgb.items():
        fill[labels == lbl] = region_rgb
    viz = mark_boundaries(fill, np.where(labels < 0, 0, labels), color=(1, 0, 1), mode="thick")
    _write(dir_ / "stage2_photo_merged.png", (viz * 255).round())


def stage2_photo_regions(
    dir_: Path, slic_count: int, merged_count: int, final_count: int, areas_px: list[int]
) -> None:
    """Count and area-distribution record: raw SLIC segment count, count
    after hierarchical merge (before the min-area floor), and the final
    region count the floor step leaves — the acceptance-check numbers for
    whoever tunes this next against a real photo."""
    dir_.mkdir(parents=True, exist_ok=True)
    lines = [
        f"slic_segments: {slic_count}",
        f"after_merge: {merged_count}",
        f"final_regions: {final_count}",
        "area_px (sorted ascending):",
        *(f"  {a}" for a in sorted(areas_px)),
    ]
    (dir_ / "stage2_photo_regions.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# --- Direction field (directionfield.py) ------------------------------------
#
# One artifact: the field rendered as short oriented strokes over the dimmed
# source image, so a human can judge the one thing no assertion can — whether
# the field actually follows the image's structure (hair flow, fur growth,
# panel edges) rather than jittering with noise. Stroke darkness carries the
# per-pixel confidence: near-black where coherence is high, faded where the
# summary API would be falling back to the house angle anyway.

_DF_STEP_PX = 8          # grid spacing between strokes
_DF_LEN_FRAC = 0.85      # stroke length as a fraction of the grid step


def direction_field(dir_: Path, rgb: np.ndarray, field) -> None:
    """`field` is a `directionfield.DirectionField` on `rgb`'s raster."""
    viz = (rgb * 0.35 + 255 * 0.65).astype(np.uint8)
    h, w = field.coherence.shape
    half = _DF_STEP_PX * _DF_LEN_FRAC / 2.0
    for y in range(_DF_STEP_PX // 2, h, _DF_STEP_PX):
        for x in range(_DF_STEP_PX // 2, w, _DF_STEP_PX):
            tx, ty = field.tangent[y, x]
            if tx == 0.0 and ty == 0.0:
                continue  # flat pixel: no direction to draw
            conf = float(field.coherence[y, x] * field.magnitude[y, x])
            shade = int(round(235 - 215 * min(1.0, conf * 3.0)))
            a = (int(round(x - tx * half)), int(round(y - ty * half)))
            b = (int(round(x + tx * half)), int(round(y + ty * half)))
            cv2.line(viz, a, b, (shade, shade, shade), 1, cv2.LINE_AA)
    _write(dir_ / "direction_field.png", viz)


def stage6_streamline_paths(dir_: Path, runs: list, size_mm) -> None:
    """The streamline tier's human-review record: every emitted run stroke in
    ink, travel faint — the one artifact that answers the tier's whole
    reason to exist (do the strokes follow the image's structure?), which no
    assertion can. Stitch penetrations dotted so spacing is judgeable too."""
    viz, to_px = _mm_canvas(size_mm)
    for run in runs:
        travel = run.kind == "travel"
        color = (200, 200, 200) if travel else (30, 30, 30)
        for a, b in zip(run.points, run.points[1:]):
            cv2.line(viz, to_px(*a), to_px(*b), color, 1, cv2.LINE_AA)
        if not travel:
            for x, y in run.points:
                cv2.circle(viz, to_px(x, y), 1, (90, 90, 200), -1)
    _write(dir_ / "stage6_streamline_paths.png", viz)


def stage6_detail_lines(dir_: Path, rgb: np.ndarray, lines_px: list) -> None:
    """The detail layer's human-review record (stage6_detail.py): every
    emitted bean line drawn in near-black ink OVER THE DIMMED SOURCE image —
    the one artifact that answers the layer's whole reason to exist (do the
    extracted lines sit on the photo's actual edges, whiskers and panel
    lines?), which no assertion can. Drawn in source-pixel space, same
    dimming as the direction-field render, because "on the edge or not" is
    only judgeable against the pixels themselves."""
    viz = (rgb * 0.35 + 255 * 0.65).astype(np.uint8)
    for pts in lines_px:
        arr = np.asarray(pts, np.float64)
        cv2.polylines(viz, [arr.round().astype(np.int32)], False,
                      (25, 25, 25), 1, cv2.LINE_AA)
    _write(dir_ / "stage6_detail_lines.png", viz)


def stage6_scanline_rows(dir_: Path, runs: list, size_mm) -> None:
    """The scan-line tonal tier's emitted geometry (stage6_scanline.py),
    drawn dark-on-light at thread weight so the halftone read — rows
    thinning and vanishing into the highlights, thickening into the shadows
    — is judgeable by eye. Travel bridges draw faint so they are visible
    without reading as tone."""
    viz, to_px = _mm_canvas(size_mm)
    for run in runs:
        color = (205, 205, 205) if run.kind == "travel" else (25, 25, 25)
        for a, b in zip(run.points, run.points[1:]):
            cv2.line(viz, to_px(*a), to_px(*b), color, 1, cv2.LINE_AA)
    _write(dir_ / "stage6_scanline_rows.png", viz)


def stage6_meander_path(dir_: Path, runs: list, size_mm) -> None:
    """The meander tonal tier's emitted geometry (stage6_meander.py), drawn
    dark-on-light at thread weight so the Reef/Sfumato read — one wandering
    line tightening and bursting into zigzag in the shadows, opening out and
    fading into bare fabric in the lights — is judgeable by eye. Travel
    (the curve traveled through highlights, and any conflict-checked break
    links) draws faint so the path's continuity is visible without reading
    as tone."""
    viz, to_px = _mm_canvas(size_mm)
    for run in runs:
        color = (205, 205, 205) if run.kind == "travel" else (25, 25, 25)
        for a, b in zip(run.points, run.points[1:]):
            cv2.line(viz, to_px(*a), to_px(*b), color, 1, cv2.LINE_AA)
    _write(dir_ / "stage6_meander_path.png", viz)


def stage6_blend_rows(dir_: Path, layer_runs: list[list], shade_rgbs: list[tuple[int, int, int]],
                      size_mm) -> None:
    """Every interleaved layer, BEFORE they merge into one fill, each drawn in
    its own shade's color. A phase-offset bug (rows that should interleave but
    land on top of each other instead) shows immediately here; it is
    invisible once the layers are merged into ordinary fill stitches.
    """
    viz, to_px = _mm_canvas(size_mm)
    for i, runs in enumerate(layer_runs):
        color = (tuple(int(v) for v in shade_rgbs[i % len(shade_rgbs)])
                if shade_rgbs else (20, 20, 20))
        for run in runs:
            for a, b in zip(run.points, run.points[1:]):
                cv2.line(viz, to_px(*a), to_px(*b), color, 1, cv2.LINE_AA)
    _write(dir_ / "stage6_blend_rows.png", viz)
