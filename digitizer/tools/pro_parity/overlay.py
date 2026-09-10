# digitizer/tools/pro_parity/overlay.py
"""Ours over the pro's, registered, on one canvas.

Pro in magenta, ours in cyan, overlap dark (multiply) — the convention every
print-registration viewer uses, so a misregistered edge reads as a coloured
fringe and an agreed one as black. Both sides go through
`stitchviz.render_design`, the Studio's lit-filament model, so what is
compared is what the product shows. Masks are taken FROM the renders
(thread pixel != fabric), so the diff masks and the picture agree by
construction. Spec §4.

    python tools/pro_parity/overlay.py --dir <out>/real/<slug>
    python tools/pro_parity/overlay.py --dir ... --crop 10 -5 40 15 --crop-name marine
    python tools/pro_parity/overlay.py --dir ... --by-thread
    python tools/pro_parity/overlay.py --dir ... --flag keep_thin_strokes=true
    python tools/pro_parity/overlay.py --dir ... --flag keep_thin_strokes=true --against baseline
"""
from __future__ import annotations

import sys
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[1]))

import pairframe as pf                                        # noqa: E402
from digitizer_core.stitchviz import render_design             # noqa: E402

WHITE = (255, 255, 255)
PRO_TINT = (255, 0, 255)      # RGB magenta
OURS_TINT = (0, 200, 255)     # RGB cyan
GHOST = 225                   # grey of the other side's silhouette on the *_only sheets
DEFAULT_PPM = 12.0
CROP_PPM = 36.0


def render_side(design: dict, frame: pf.Frame) -> np.ndarray:
    d = pf.pin_frame(design, frame.bounds_units)
    img = render_design(d, px_per_mm=frame.ppm, fabric_bgr=WHITE, pad_mm=frame.pad_mm, lit=True)
    # Ensure consistent image size even when design is restricted to empty.
    # When render_design operates on an empty design, it may produce a smaller
    # image; resize to match the frame's expected dimensions.
    try:
        bounds = frame.bounds_units
        if isinstance(bounds, (tuple, list)) and len(bounds) >= 4:
            min_x, min_y, max_x, max_y = bounds[0], bounds[1], bounds[2], bounds[3]
            expected_w = int((max_x - min_x + frame.pad_mm * 2) * frame.ppm + 0.5)
            expected_h = int((max_y - min_y + frame.pad_mm * 2) * frame.ppm + 0.5)
            if img.shape[0] != expected_h or img.shape[1] != expected_w:
                img = cv2.resize(img, (expected_w, expected_h))
    except (TypeError, ValueError, AttributeError):
        pass
    return img


def thread_mask(img: np.ndarray) -> np.ndarray:
    return np.any(img < 250, axis=2)


def tint(img: np.ndarray, rgb: tuple) -> np.ndarray:
    """Thread pixels take the tint, keeping the filament shading as a
    brightness ramp (0.35..1.0 of the tint); fabric stays white."""
    m = thread_mask(img)
    L = img.astype(np.float32).mean(axis=2) / 255.0
    out = np.full_like(img, 255)
    bgr = (rgb[2], rgb[1], rgb[0])
    for c in range(3):
        ch = out[..., c]
        ch[m] = np.clip(bgr[c] * (0.35 + 0.65 * L[m]), 0, 255).astype(np.uint8)
    return out


def _only_sheet(only: np.ndarray, other: np.ndarray, rgb: tuple) -> np.ndarray:
    out = np.full(only.shape + (3,), 255, np.uint8)
    out[other] = GHOST
    out[only] = (rgb[2], rgb[1], rgb[0])
    return out


def _restrict(design: dict, blocks: set | None) -> dict:
    """The design's stitches limited to the given block indices (colour
    records kept so colours still advance)."""
    if blocks is None:
        return design
    keep, bi = [], 0
    for s in design["stitches"]:
        if s["type"] == "color":
            bi += 1
            keep.append(s)
        elif s["type"] in ("jump", "trim", "end") or bi in blocks:
            keep.append(s)
    return dict(design, stitches=keep)


def render_pair(pair: pf.Pair, reg: pf.Reg, ppm: float = DEFAULT_PPM, crop_mm=None,
                only_pro_block: int | None = None, only_ours_blocks: set | None = None,
                ours_path: Path | None = None, ours_rgb: list | None = None) -> dict:
    pro_d = pf.design_for(pair.pro_path, None, pair.pro_rgb, f"{pair.slug} pro")
    ours_d = pf.design_for(ours_path or pair.ours_path, reg, ours_rgb or pair.ours_rgb, f"{pair.slug} ours")
    # Compute frame from unrestricted designs to avoid sentinel bounds when restriction empties a side
    frame = pf.frame_for([pro_d, ours_d], ppm, crop_mm=crop_mm)
    # Apply restrictions only for rendering
    pro_d = _restrict(pro_d, {only_pro_block} if only_pro_block is not None else None)
    ours_d = _restrict(ours_d, only_ours_blocks)
    pro = render_side(pro_d, frame)
    ours = render_side(ours_d, frame)
    pm, om = thread_mask(pro), thread_mask(ours)
    pt, ot = tint(pro, PRO_TINT), tint(ours, OURS_TINT)
    over = (pt.astype(np.float32) * ot.astype(np.float32) / 255.0).astype(np.uint8)
    return {"frame": frame, "pro": pro, "ours": ours, "pro_mask": pm, "ours_mask": om,
            "overlay": over, "pro_only": pm & ~om, "ours_only": om & ~pm,
            "pro_only_img": _only_sheet(pm & ~om, om, PRO_TINT),
            "ours_only_img": _only_sheet(om & ~pm, pm, OURS_TINT)}


def _titled(img: np.ndarray, title: str) -> np.ndarray:
    bar = np.full((22, img.shape[1], 3), 255, np.uint8)
    cv2.putText(bar, title, (6, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1, cv2.LINE_AA)
    return np.vstack([bar, img])


def write_overlay_set(out_dir: Path, r: dict, title: str, suffix: str = "") -> list:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    files = {
        f"overlay{suffix}.png": _titled(r["overlay"], title),
        f"pro_only{suffix}.png": _titled(r["pro_only_img"], title + "  PRO ONLY"),
        f"ours_only{suffix}.png": _titled(r["ours_only_img"], title + "  OURS ONLY"),
        f"flicker_pro{suffix}.png": r["pro"],
        f"flicker_ours{suffix}.png": r["ours"],
    }
    written = []
    for name, img in files.items():
        p = out_dir / name
        cv2.imwrite(str(p), img)
        written.append(p)
    return written


def title_for(pair: pf.Pair, reg: pf.Reg, extra: str = "") -> str:
    return (f"{pair.slug} {pair.width_mm:.1f} mm  iou {reg.iou:.2f}  scale {reg.scale:.3f}"
            f"{'  flipY' if reg.flip_y else ''}{('  ' + extra) if extra else ''}")
