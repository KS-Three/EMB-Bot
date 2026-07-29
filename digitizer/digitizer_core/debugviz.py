"""Per-stage debug PNGs — the visual record for reviewing pipeline behavior.

Written only when cfg.debug_dir is set (never in the service's hot path).
Filenames are stage-prefixed so the directory reads in pipeline order.
"""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from .threads import CHART


def _write(path: Path, rgb: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(path), cv2.cvtColor(rgb.astype(np.uint8), cv2.COLOR_RGB2BGR))


def stage1(dir_: Path, rgb: np.ndarray, bg_mask: np.ndarray) -> None:
    _write(dir_ / "stage1_denoised.png", rgb)
    over = rgb.copy()
    over[bg_mask] = (over[bg_mask] * 0.25 + np.array([255, 0, 255]) * 0.75).astype(np.uint8)
    _write(dir_ / "stage1_bg.png", over)


def stage2(dir_: Path, labels: np.ndarray, thread_indices: list[int]) -> None:
    rng = np.random.default_rng(7)
    palette = rng.integers(40, 235, size=(max(1, labels.max() + 1), 3))
    viz = np.zeros(labels.shape + (3,), np.uint8)
    for j in range(labels.max() + 1):
        viz[labels == j] = palette[j]
    _write(dir_ / "stage2_labels.png", viz)

    snapped = np.full(labels.shape + (3,), 255, np.uint8)
    for j, t in enumerate(thread_indices):
        snapped[labels == j] = CHART[t].rgb
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


def stage4(dir_: Path, rgb: np.ndarray, regions, px_per_mm: float, art_bbox) -> None:
    x0, y0, x1, y1 = art_bbox
    cx, cy = (x0 + x1) / 2.0, (y0 + y1) / 2.0
    viz = (rgb * 0.3 + 255 * 0.7).astype(np.uint8)

    def to_px(coords) -> np.ndarray:
        a = np.asarray(coords, np.float64)
        a[:, 0] = a[:, 0] * px_per_mm + cx
        a[:, 1] = a[:, 1] * px_per_mm + cy
        return a.astype(np.int32)

    for r in regions:
        thread_rgb = tuple(int(v) for v in CHART[r.thread_index].rgb)
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
